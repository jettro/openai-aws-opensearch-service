import logging
from datetime import datetime

from opensearchpy import OpenSearch, RequestsHttpConnection

search_log = logging.getLogger("search")


class OpenSearchClient:
    def __init__(self, config: dict, alias_name: str = None):
        # auth = (username, password)

        self.opensearch = OpenSearch(
            hosts=[{'host': config["host"], 'port': config['port']}],
            use_ssl=True,
            verify_certs=True,
            http_auth=config["auth"],
            connection_class=RequestsHttpConnection
        )
        if alias_name:
            self.alias_name = alias_name

    def ping(self):
        if self.opensearch.ping():
            search_log.info('Connected to OpenSearch')
            return True
        else:
            search_log.warning('Could not connect to OpenSearch')
            return False

    def create_index(self):
        """
        Create a new index. Name of the index is a combination of the configured ALIAS_NAME and a time stamp in the format
        of YearMonthDayHourMinuteSecond. Before the index is created, we remove it if it already exists. The settings
        and mappings are obtained from the shoes_index.json in the config folder.
        :return: The name of the created index
        """
        index_name = f'{self.alias_name}-{datetime.now().strftime("%Y%m%d%H%M%S")}'

        self.opensearch.indices.delete(index=index_name, ignore_unavailable=True)
        self.opensearch.indices.create(index=index_name)

        search_log.info(f'Created a new index with the name {index_name}')
        return index_name

    def switch_alias_to(self, index_name: str):
        """
        Checks if the alias as configured is already available, if so, remove all indexes it points to. When finished add
        the provided index to the alias.
        :param index_name: Name of the index to assign to the alias
        :return:
        """
        search_log.info(f'Assign alias {self.alias_name} to {index_name}')
        body = {
            "actions": [
                {"remove": {"index": f'{self.alias_name}-*', "alias": self.alias_name}},
                {"add": {"index": index_name, "alias": self.alias_name}}
            ]
        }
        self.opensearch.indices.update_aliases(body=body)

    def index_product(self, product, index_name: str):
        """
        Send the provided shoe to Elasticsearch to index that shoe into the provided index.
        :param product: The Product to index
        :param index_name: The index to use for indexing the shoe
        :return:
        """
        search_log.info(f'Indexing shoe: {product["id"]} into index with name {index_name}')
        self.opensearch.index(index=index_name, id=product["id"], body=product)

    def search(self, body, explain: bool = False):
        search_results = self.opensearch.search(index=self.alias_name, body=body, explain=explain)
        return search_results

    def set_component_template(self, name, body):
        self.opensearch.cluster.put_component_template(name=name, body=body)

    def set_index_template(self, name, body):
        self.opensearch.indices.put_index_template(name=name, body=body)

    def does_index_template_exist(self, name: str):
        return self.opensearch.indices.exists_index_template(name=name)

    def get_index_template(self, name: str):
        return self.opensearch.indices.get_index_template(name=name)

    def does_component_template_exist(self, name: str):
        return self.opensearch.cluster.exists_component_template(name=name)

    def get_component_template(self, name: str):
        return self.opensearch.cluster.get_component_template(name=name)

    def delete_index(self, index_name: str):
        self.opensearch.indices.delete(index=index_name, ignore_unavailable=True)
