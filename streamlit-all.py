import json
import os

import langchain
import streamlit as st
from langchain.vectorstores import OpenSearchVectorSearch
from langchain.embeddings import OpenAIEmbeddings
from opensearchpy import RequestsHttpConnection
from dotenv import load_dotenv
from langchain.schema import SystemMessage
from langchain.agents import OpenAIFunctionsAgent, AgentExecutor
from langchain.tools import Tool
from langchain.chat_models import ChatOpenAI

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


def execute_product_search(query: str):
    found_docs = vector_store_products.similarity_search_with_score(query=query, text_field="title",
                                                                    vector_field="title_vector")
    results = []
    for doc, _score in found_docs:
        results.append({"title": doc.page_content, "score": _score, "image_name": doc.metadata["image_name"]})

    return {
        "tool": "product_search",
        "result": results
    }


def execute_content_search(query: str):
    return {
        "tool": "content_search",
        "result": content_chain.run(query)
    }


def execute_opening_hours(city: str):
    body = {
        "query": {
            "match": {
                "city": city
            }
        }
    }
    search_result = os_client.search(body=body, size=1, index_name="sg-stores")
    result = []
    if search_result["hits"]["total"]["value"] > 0:
        result = search_result["hits"]["hits"][0]["_source"]

    return {
        "tool": "opening_hours",
        "result": result
    }


def init_agent() -> AgentExecutor:
    llm = ChatOpenAI(model="gpt-4-0613", temperature=0, openai_api_key=os.getenv('OPEN_AI_API_KEY'))
    system_message = SystemMessage(
        content="You are a web service returning the pure json without a change.")
    prompt = OpenAIFunctionsAgent.create_prompt(system_message=system_message)

    tools = [
        Tool(name="ExecuteContentSearch",
             func=execute_content_search,
             description="Useful for obtaining answers to questions about help for the website, your account and "
                         "sustainability."
             ),
        Tool(name="ExecuteProductSearch",
             func=execute_product_search,
             description="Useful for finding products related to the search terms that are provided."
             ),
        Tool(name="ExecuteOpeningHours",
             func=execute_opening_hours,
             description="Useful for obtaining opening hours of a store in city that is provided."
             ),
    ]

    agent = OpenAIFunctionsAgent(llm=llm, tools=tools, prompt=prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=False)


if __name__ == '__main__':
    load_dotenv()

    langchain.debug = False

    os_client, config = init_opensearch_client()
    vector_store_products = init_product_search()
    content_chain = init_content_search()
    agent_executor = init_agent()

    # Start Streamlit app
    st.set_page_config(layout="wide")
    st.title = "LEGO® BrickHeadz - Store™"

    st.header('LEGO® BrickHeadz - Store™', divider='rainbow')

    the_query = st.text_input('What are you looking for?', key="search_terms_input")

    if the_query:
        agent_response = agent_executor.run(the_query)
        response = json.loads(agent_response)
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
