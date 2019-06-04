import sys
import deploy_utils
from logger import Logger

def run(bucket):
  du = deploy_utils.DeployUtil(bucket)
  logger = Logger()
  logger.log("Running: python {0}".format(' '.join(sys.argv)))

  # Get code versions to compare
  sha_production = du.sha_for_stage_file('current.production.txt')
  sha_staging = du.sha_for_stage_file('current.staging.txt')
  sha_local = deploy_utils.sha_for_repo()

  # Sync code if necessary
  #
  # local       staging     production      what to do
  # -----       -------     ----------      ----------
  # v1          v1          v1              Nothing
  # v1          v2          v2              Nothing
  # v2          v1          v1              Nothing
  # v2          v2          v1              Push local -> production
  # v1          v2          v1              Throw an error: local does not match staging
  # v3          v2          v1              Throw an error: local does not match staging
  if sha_staging == sha_production:
    logger.log('Production code already matches staging, nothing to do.')
  elif sha_local != sha_staging:
    logger.log("Local code doesn't match staging {}, something's wrong!".format(sha_staging))
    exit(1)
  else:
    logger.log('Deploying code from local to production.')
    exit_code = du.deploy_code_to_stage('production')
    if exit_code != 0:
      logger.log('Deploy to production failed with exit code {}.'.format(exit_code))
      exit(exit_code)

  # Promote model
  logger.log('Promoting model from staging to production.')
  du.promote_model('current.staging.txt', 'current.production.txt')

  # Log result
  logger.log("Finished promoting.")
  logger.flush()

