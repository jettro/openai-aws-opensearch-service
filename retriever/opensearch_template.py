import logging

from retriever import OpenSearchClient
from util import load_json_body_from_file

tpl_logging = logging.getLogger("template")


class OpenSearchTemplate:

    def __init__(self,
                 client: OpenSearchClient,
                 index_template_name: str,
                 component_name_settings: str,
                 component_name_dyn_mappings: str,
                 component_name_mappings: str):
        self.client = client
        self.index_template_name = index_template_name
        self.component_name_settings = component_name_settings
        self.component_name_dyn_mappings = component_name_dyn_mappings
        self.component_name_mappings = component_name_mappings

    def create_update_template(self) -> list:
        """ Check the version of the current template and update if necessary """
        tpl_logging.info("Initialize or update the product template in OpenSearch.")

        return [
            self.__update_component(component_name=self.component_name_settings),
            self.__update_component(component_name=self.component_name_dyn_mappings),
            self.__update_component(component_name=self.component_name_mappings),
            self.__update_index_template()
        ]

    def __update_component(self, component_name: str):
        body = load_json_body_from_file(file_name=f"./config_files/{component_name}.json")
        required_version = body['version']
        component_needs_update = self.__component_needs_update(component_name=component_name,
                                                               current_version=required_version)
        if component_needs_update:
            self.client.set_component_template(name=component_name, body=body)
            result = f"Update the component template {component_name} to version {required_version}."
        else:
            result = f"The version {required_version} of the component template {component_name} is up-to-date"

        return result

    def __update_index_template(self):
        body = load_json_body_from_file(file_name=f"./config_files/{self.index_template_name}.json")
        required_version = body['version']
        template_needs_update = self.__template_needs_update(template_name=self.index_template_name,
                                                             current_version=required_version)

        if template_needs_update:
            self.client.set_index_template(name=self.index_template_name, body=body)
            result = f"Update the template to version {required_version}."
        else:
            result = f"The version {required_version} of the index template is up-to-date"

        return result

    def __template_needs_update(self, template_name: str, current_version):
        """ The template needs to update if there is no template or if the versions do not match """
        if not self.client.does_index_template_exist(name=template_name):
            tpl_logging.debug("The template with name '%s' is not found", template_name)
            return True

        response = self.client.get_index_template(name=template_name)
        tpl_logging.debug(response)

        templates = response['index_templates']
        if len(templates) != 1:
            raise Exception("We cannot have matching more than 1 template while looking for " + template_name)

        index_template = templates[0]['index_template']
        return not (index_template.get("version") == current_version)

    def __component_needs_update(self, component_name: str, current_version):
        """ The template needs to update if there is no template or if the versions do not match """
        tpl_logging.debug("Obtain the component template with name '%s'", component_name)
        if not self.client.does_component_template_exist(name=component_name):
            tpl_logging.debug("The component template with name '%s' is not found", component_name)
            return True

        response = self.client.get_component_template(name=component_name)
        tpl_logging.debug(response)

        components = response['component_templates']
        if len(components) != 1:
            raise Exception("We cannot have matching more than 1 component while looking for " + component_name)

        component_template = components[0]['component_template']
        return not (component_template.get("version") == current_version)
