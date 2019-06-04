import sys
import deploy_utils
from logger import Logger

def run(bucket, model_version_to_push=None):
  du = deploy_utils.DeployUtil(bucket)
  # Instantiate logger
  logger = Logger()
  logger.log("Running: python {0}".format(' '.join(sys.argv)))

  # Push model files to S3 if necessary
  if not model_version_to_push:
    model_version_to_push = du.push_model(logger)
    logger.log('Pushed model version {} to S3.'.format(model_version_to_push))

  # Make sure the requested model is on S3
  model_is_on_s3 = du.model_version_exists(model_version_to_push)
  if model_version_to_push and model_is_on_s3:
    logger.log('Requested model version is already on S3, nothing to do.')
  elif model_version_to_push and not model_is_on_s3:
    logger.log('Requested model version is not on S3. Did you make a typo?')
    exit(1)

  # Get code versions to compare
  sha_previous = du.sha_for_stage_file('current.staging.txt')
  sha_next = du.sha_for_model_version(model_version_to_push)
  sha_current = deploy_utils.sha_for_repo()

  # Sync code if necessary
  if sha_previous == sha_next:
    logger.log('Staging code already matches target version, nothing to do.')
  elif sha_current != sha_next:
    # If using the directory flag, you might have to check out the previous
    # version that the model was created using
    logger.log("Local code doesn't match target version ({}), something's wrong!".format(sha_next))
    exit(1)
  else:
    logger.log('Deploying code from local to staging.')
    exit_code = du.deploy_code_to_stage('staging')
    if exit_code != 0:
      logger.log('Deploy to staging failed with exit code {}.'.format(exit_code))
      exit(exit_code)

  # Point stage file to model version
  stage_file = 'current.staging.txt'
  logger.log('Pointing stage file {} to model version {}.'.format(stage_file, model_version_to_push))
  du.point_stage_file_to_model_version(stage_file, model_version_to_push)

  # Log result
  logger.log("Finished pushing.")
  logger.flush()

