import os

import langchain
import streamlit as st
from dotenv import load_dotenv
from langchain.chains.openai_functions import create_openai_fn_chain
from langchain.chat_models import ChatOpenAI
from langchain.embeddings import OpenAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.vectorstores import OpenSearchVectorSearch
from opensearchpy import RequestsHttpConnection

from retriever import find_auth_opensearch, OpenSearchClient


def init_opensearch_client():
    os_config = find_auth_opensearch()
    return OpenSearchClient(os_config, alias_name="sg-products"), os_config


def init_product_search():
    return OpenSearchVectorSearch(
        index_name="sg-products",
        embedding_function=OpenAIEmbeddings(openai_api_key=os.getenv('OPEN_AI_API_KEY')),
        opensearch_url=f"https://{config['host']}:{config['port']}",
        use_ssl=True,
        verify_certs=True,
        http_auth=config["auth"],
        connection_class=RequestsHttpConnection
    )


def init_content_search():
    vector_store = OpenSearchVectorSearch(
        index_name="sg-content",
        embedding_function=OpenAIEmbeddings(openai_api_key=os.getenv('OPEN_AI_API_KEY')),
        opensearch_url=f"https://{config['host']}:{config['port']}",
        use_ssl=True,
        verify_certs=True,
        http_auth=config["auth"],
        connection_class=RequestsHttpConnection
    )

    from langchain.chains import RetrievalQA
    from langchain import PromptTemplate, OpenAI

    prompt_template = """Use the context to answer the question. If you don't know the 
        answer, just say that you don't know, don't make up an answer.

        {context}

        Question: {question}:"""

    custom_prompt = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )

    chain_type_kwargs = {"prompt": custom_prompt}
    return RetrievalQA.from_chain_type(
        llm=OpenAI(openai_api_key=os.getenv('OPEN_AI_API_KEY')),
        chain_type="stuff",
        retriever=vector_store.as_retriever(),
        chain_type_kwargs=chain_type_kwargs
    )


def execute_product_search(query: str) -> dict:
    """Useful for finding products related to the search terms that are provided.

    Args:
        query: Query to search products for
    """
    found_docs = vector_store_products.similarity_search_with_score(query=query,
                                                                    text_field="title",
                                                                    vector_field="title_vector")
    results = []
    for doc, _score in found_docs:
        results.append({"title": doc.page_content, "score": _score, "image_name": doc.metadata["image_name"]})

    return {
        "tool": "product_search",
        "result": results
    }


def execute_content_search(query: str) -> dict:
    """Useful for obtaining answers to questions about help for the website, your account and sustainability.

    Args:
        query: Query to use as input for the content search
    """
    return {
        "tool": "content_search",
        "result": content_chain.run(query)
    }


def execute_opening_hours(city: str) -> dict:
    """Useful for obtaining opening hours of a store in city that is provided.

    Args:
        city: Name of the city to search for
    """
    body = {
        "query": {
            "match": {
                "city": city
            }
        }
    }
    search_result = os_client.search(body=body, size=1, index_name="sg-stores")
    results = []
    if search_result["hits"]["total"]["value"] > 0:
        results = search_result["hits"]["hits"][0]["_source"]

    return {
        "tool": "opening_hours",
        "result": results
    }


def init_fn_chain():
    llm = ChatOpenAI(model="gpt-4-0613", temperature=0, openai_api_key=os.getenv('OPEN_AI_API_KEY'))
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a system to search for answers on a provided question."),
            ("human", "Make calls to the relevant function to using the following input: {input}"),
            ("human", "Tip: Make sure to answer in the correct format"),
        ]
    )

    return create_openai_fn_chain(
        functions=[execute_opening_hours, execute_content_search, execute_product_search],
        llm=llm,
        prompt=prompt,
        verbose=True
    )


if __name__ == '__main__':
    load_dotenv()

    langchain.debug = False

    os_client, config = init_opensearch_client()
    vector_store_products = init_product_search()
    content_chain = init_content_search()

    # Start Streamlit app
    st.set_page_config(layout="wide")
    st.title = "LEGO® BrickHeadz - Store™"

    st.header('LEGO® BrickHeadz - Store™', divider='rainbow')

    the_query = st.text_input('What are you looking for?', key="search_terms_input")

    functions_map = {
        'execute_opening_hours': execute_opening_hours,
        'execute_content_search': execute_content_search,
        'execute_product_search': execute_product_search
    }

    if the_query:
        the_chain = init_fn_chain()
        chain_response = the_chain.run(the_query)
        print(chain_response)
        function_name = chain_response["name"]
        args = chain_response["arguments"]

        if function_name not in functions_map:
            st.write("Could not decide which content search to perform.")
        else:
            response = functions_map[function_name](**args)

            if response and response["tool"] == "product_search":
                for item in response["result"]:
                    st.image(image="./images/" + item['image_name'],
                             caption=item['title'],
                             width=200)
                    st.write(item['score'])

            if response and response["tool"] == "content_search":
                st.write(response["result"])
            if response and response["tool"] == "opening_hours":
                result = response['result']
                st.subheader(f"Store: {result['store_name']} te {result['city']}")
                st.write(f"{result['street']} - {result['telephone']}")
                for ot in result["opening_hours"]:
                    st.write(f"{ot['week_day']} {ot['open_time']} - {ot['closing_time']}")
