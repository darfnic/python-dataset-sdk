""""
meteoblue dataset client
"""

import aiohttp
import asyncio
import logging
from contextlib import asynccontextmanager
import Dataset_pb2


class ClientConfig(object):

    def __init__(self, apikey: str):
        # urls
        self.statusUrl = 'http://mystaging.meteoblue.com/queue/status/%s'  # following queue id
        # following api key
        self.queryUrl = 'http://mystaging.meteoblue.com/dataset/query?apikey=%s'
        self.resultUrl = 'http://queueresults.meteoblue.com/%s'  # following query id

        # http
        self.httpMaxRetryCount = 5

        # other config
        self.apikey = apikey


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class ApiError(Error):
    """Exception raised for errors in the input.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message):
        self.message = message


class Client(object):

    def __init__(self, apikey: str):
        self._config = ClientConfig(apikey)

    @asynccontextmanager
    async def _fetch(self, session: aiohttp.ClientSession, method: str, url: str, retryCount=0, json: any = None):
        """
        Fetch data from an URL and try for error 5xx or timeouts.
        Codes other than 2xx will throw an exception.

        :param url: url to make http get on
        :param retryCount: number of retries to attempt
        :return:
        """
        logging.debug('Getting url %s %s' % (method, url))

        async with session.request(method, url, json=json) as response:
            # return if successful
            if 200 <= response.status <= 299:
                yield response
                return

            # retry mechanism
            shouldRetry = retryCount < self._config.httpMaxRetryCount
            # check if request timed out or backend threw an error
            if shouldRetry and (response.status == 408 or 500 <= response.status <= 599):
                # 408: HTTP request timeout
                # 500-599: HTTP backend error
                await asyncio.sleep(1)
                async with self._fetch(session, method, url, retryCount + 1) as response:
                    yield response
                    return

            # meteoblue APIs return a JSON encoded error message
            if response.status == 400:
                json = await response.json()
                logging.debug("API returned error message: %s" %
                              json["error_message"])
                raise ApiError(json["error_message"])

            logging.error('API returned unexpected error: %s' %
                          response.content)
            raise Exception("API returned unexpected error", response.content)

    @asynccontextmanager
    async def _runOnJobQueue(self, session: aiohttp.ClientSession, params: dict):
        """
        Run the query on a job queue
        :param session: ClientSession
        :param params: query parameters for meteoblue dataset api
        :return: ClientResponse object from aiohttp lib
        """

        # Start job on a job queue
        logging.info("Starting job on queue")
        params["runOnJobQueue"] = True
        url = self._config.queryUrl % self._config.apikey
        async with self._fetch(session, "POST", url, json=params) as response:
            responseJson = await response.json()

        # Wait until the job is finished
        jobId = responseJson['id']
        logging.info("Waiting until job has finished (job id %s)" % jobId)
        statusUrl = self._config.statusUrl % str(jobId)
        while True:
            async with self._fetch(session, "GET", statusUrl) as response:
                json = await response.json()
            status = json['status']
            logging.debug('Job status is %s' % status)
            if status == 'finished':
                break
            if status == 'deleted':
                raise ApiError("Job was canceled")
            if status == 'error':
                raise ApiError(json["error_message"])
            logging.info(
                'Waiting 5 seconds for job to complete. Status: %s, job id %s' % (status, jobId))
            await asyncio.sleep(5)

        # Fetch the job queue result
        resultUrl = self._config.resultUrl % jobId
        logging.debug('Fetching result for job id %s' % jobId)
        async with self._fetch(session, "GET", resultUrl) as response:
            yield response

    @asynccontextmanager
    async def query(self, params: dict):
        """
        Query meteoblue dataset api asynchronously, run multiple queries in parallel
        :param params: query parameters, see https://docs.meteoblue.com/en/apis/environmental-data/dataset-api
        :return: ClientResponse object from aiohttp lib
        """

        async with aiohttp.ClientSession() as session:
            # Try to run the job directly
            # In case the API throws an error, try to run it on a job queue
            try:
                url = self._config.queryUrl % self._config.apikey
                async with self._fetch(session, "POST", url, json=params) as response:
                    yield response
            except ApiError as error:
                # Run on a job queue in case the api throws the error
                if error.message != "This job must be executed on a job-queue":
                    raise
                async with self._runOnJobQueue(session, params) as response:
                    yield response

    async def asProtobuf(self, params: dict):
        """
        Query meteoblue dataset api asynchronously, and expect the result to be a meteoblue dataset api protobuf
        :param params: query parameters, see https://docs.meteoblue.com/en/apis/environmental-data/dataset-api
        :return: ClientResponse object from aiohttp lib
        """

        params['format'] = 'protobuf'

        async with self.query(params) as response:
            data = await response.read()
            msg = Dataset_pb2.DatasetApiProtobuf()
            msg.ParseFromString(data)
            return msg

    def query_seq(self, params: dict):
        """
        Query meteoblue dataset api synchronously for sequential usage
        :param params: query parameters, see https://docs.meteoblue.com/en/apis/environmental-data/dataset-api
        :return: ClientResponse object from aiohttp lib
        """
        # return asyncio.run(self._query(params))


async def main():
    query1 = {"units": {"temperature": "C", "velocity": "km/h", "length": "metric", "energy": "watts"}, "geometry": {"type": "Polygon", "coordinates": [[[2.96894, 46.041886], [2.96894, 48.216537], [10.989692, 48.216537], [10.989692, 46.041886], [2.96894, 46.041886]]]}, "format": "json", "timeIntervals": [
        "2017-01-01T+00:00/2019-01-31T+00:00"], "timeIntervalsAlignment": "none", "queries": [{"domain": "NEMSGLOBAL", "gapFillDomain": None, "timeResolution": "hourly", "codes": [{"code": 11, "level": "2 m above gnd"}], "transformations": [{"type": "aggregateTimeInterval", "aggregation": "mean"}, {"type": "spatialTotalAggregate", "aggregation": "mean"}]}]}

    query2 = {"units": {"temperature": "C", "velocity": "km/h", "length": "metric", "energy": "watts"}, "geometry": {"type": "MultiPoint", "coordinates": [[7.57327, 47.558399, 279]], "locationNames": ["Basel"]}, "format": "json", "timeIntervals": [
        "2019-01-01T+00:00/2019-01-01T+00:00"], "timeIntervalsAlignment": "none", "queries": [{"domain": "NEMSGLOBAL", "gapFillDomain": None, "timeResolution": "hourly", "codes": [{"code": 11, "level": "2 m above gnd"}]}]}
    # import mbdataset
    mb = Client(apikey='xxxxx')  # ask for key
    a = await mb.asProtobuf(query2)
    logging.debug(a)
    #query1 = asyncio.create_task(mb.query_async(qparams))
    #query2 = asyncio.create_task(mb.query_async(qparams))
    # res1 = await query1
    # res2 = await query2
    # async with mb.query(query1) as response:
    #    json = await response.json()
    #    print(json)
    # print(res1)
    # print(res2)


if __name__ == "__main__":
    logging.basicConfig(
        # filename=self._config.log_file,
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.DEBUG,
        datefmt='%Y-%m-%d %H:%M:%S')

    asyncio.run(main())
