import threading

import google_auth_httplib2
import httplib2
from googleapiclient import discovery

from prowler.lib.logger import logger
from prowler.providers.gcp.gcp_provider import generate_client


class GCPService:
    def __init__(self, service, audit_info, region="global", api_version="v1"):
        # We receive the service using __class__.__name__ or the service name in lowercase
        # e.g.: APIKeys --> we need a lowercase string, so service.lower()
        self.service = service.lower() if not service.islower() else service
        self.credentials = audit_info.credentials
        self.api_version = api_version
        self.default_project_id = audit_info.default_project_id
        self.region = region
        self.client = generate_client(service, api_version, audit_info)
        # Only project ids that have their API enabled will be scanned
        self.project_ids = self.__is_api_active__(audit_info.project_ids)

    def __get_client__(self):
        return self.client

    def __threading_call__(self, call, iterator):
        threads = []
        for value in iterator:
            threads.append(threading.Thread(target=call, args=(value,)))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def __get_AuthorizedHttp_client__(self):
        return google_auth_httplib2.AuthorizedHttp(
            self.credentials, http=httplib2.Http()
        )

    def __is_api_active__(self, audited_project_ids):
        project_ids = []
        for project_id in audited_project_ids:
            try:
                client = discovery.build("serviceusage", "v1")
                request = client.services().get(
                    name=f"projects/{project_id}/services/{self.service}.googleapis.com"
                )
                response = request.execute()
                if response.get("state") != "DISABLED":
                    project_ids.append(project_id)
                else:
                    logger.error(
                        f"{self.service} API has not been used in project {project_id} before or it is disabled. Enable it by visiting https://console.developers.google.com/apis/api/dataproc.googleapis.com/overview?project={project_id} then retry."
                    )
            except Exception as error:
                logger.error(
                    f"{error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
                )
        return project_ids
