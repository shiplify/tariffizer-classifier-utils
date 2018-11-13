import os
import errno
import boto
import datetime
from boto.s3.key import Key
#  from logger import Logger

class DeployUtil(object):

  def __init__(self, bucket_name):
    conn = boto.connect_s3(host='s3.amazonaws.com')
    self.bucket = conn.get_bucket(bucket_name)

  def model_version_for_stage_file(self, stage_file_name):
    key_obj = Key(self.bucket)
    key_obj.key = stage_file_name
    return key_obj.get_contents_as_string().strip()

  def sha_for_model_version(self, model_version):
    key_obj = Key(self.bucket)
    key_obj.key = model_version + '/sha.txt'
    return key_obj.get_contents_as_string()

  def file_exists_at_key(self, key):
    key_obj = Key(self.bucket)
    key_obj.key = key
    return key_obj.exists()

  def download_file_at_key_to_path(self, remote_key, local_path):
    if not self.file_exists_at_key(remote_key): return None

    # Make sure local dir structure exists
    dir_name = os.path.dirname(local_path)
    self.mkdir_p(dir_name)

    # Download file
    key_obj = Key(self.bucket)
    key_obj.key = remote_key
    key_obj.get_contents_to_filename(local_path)

    return local_path

  def file_contents_at_key(self, remote_key):
    if not self.file_exists_at_key(remote_key): return None

    # Get file contents
    key_obj = Key(self.bucket)
    key_obj.key = remote_key
    return key_obj.get_contents_as_string()

  def mkdir_p(self, path):
    try:
      os.makedirs(path)
    except OSError as exc:
      if exc.errno == errno.EEXIST and os.path.isdir(path):
        pass
      else:
        raise

  def sha_for_stage_file(self, stage_file_name):
    if not self.file_exists_at_key(stage_file_name): return None
    model_version = self.model_version_for_stage_file(stage_file_name)
    return self.sha_for_model_version(model_version)

  def deploy_code_to_stage(self, stage):
    cmd = os.system("zappa update {}".format(stage))
    return os.WEXITSTATUS(cmd)

  # Copies a text file from stage_file_from to stage_file_to.
  #
  # stage_file_from and stage_file_to are both filenames of files containing model version
  # numbers (datetimes).
  #
  # stage_file_from (ex: current.staging.txt) is the file that points to the version
  # of the model that we want to deploy from.
  #
  # stage_file_to (ex: current.production.txt) is the file that we want to update with the
  # new version of the model (to match the contents of stage_file_from).
  def promote_model(self, stage_file_from, stage_file_to):
    model_version = self.model_version_for_stage_file(stage_file_from)
    self.point_stage_file_to_model_version(stage_file_to, model_version)

  def point_stage_file_to_model_version(self, stage_file, model_version):
    key_obj = Key(self.bucket)
    key_obj.key = stage_file
    key_obj.set_contents_from_string(model_version)

  def model_version_exists(self, model_version):
    return self.file_exists_at_key(model_version + '/sha.txt')

  def push_model(self, logger=None):
    # Check for all required files
    required_files = ['model.pkl', 'classes.pkl', 'train.log', 'cross_validate.log', 'scores.json', 'sha.txt']
    missing_files = []
    for required_file in required_files:
      file_path = 'classifier/' + required_file
      if not os.path.isfile(file_path):
        missing_files.append(required_file)

    # Error if we have any missing files
    if missing_files:
      logger.log("Missing required files: {0}".format(missing_files))
      logger.log("Please make sure you've run cross_validate and train before running push, or run with --model_version declared.")
      exit(1)

    # Push files to s3
    model_version = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    for required_file in required_files:
      file_path = 'classifier/' + required_file
      key_obj = Key(self.bucket)
      key_obj.key = model_version + "/" + required_file
      key_obj.set_contents_from_filename(file_path)
      logger.log('Posted {} to S3.'.format(key_obj.key))
      os.remove(file_path)
    return model_version

def sha_for_repo():
  import git
  repo = git.Repo(search_parent_directories=True)
  return repo.head.object.hexsha

