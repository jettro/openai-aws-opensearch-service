import os
import streamlit as st
from langchain.vectorstores import OpenSearchVectorSearch
from langchain.embeddings import OpenAIEmbeddings
from opensearchpy import RequestsHttpConnection
from dotenv import load_dotenv

from retriever import find_auth_opensearch, OpenSearchClient

load_dotenv()


def init_opensearch_client():
    config = find_auth_opensearch()
    return OpenSearchClient(config, alias_name="sg-products"), config


def init_langchain_vectorstore(os_search_url: str):
    return OpenSearchVectorSearch(
        index_name="sg-products",
        embedding_function=OpenAIEmbeddings(openai_api_key=os.getenv('OPEN_AI_API_KEY')),
        opensearch_url=os_search_url,
        use_ssl=True,
        verify_certs=True,
        http_auth=config["auth"],
        connection_class=RequestsHttpConnection
    )


def execute_lexical_search(client: OpenSearchClient, query: str):
    body = {"query": {"match": {"title": query}}}
    found_docs = client.search(body=body, explain=False)

    return [{"score": hit['_score'],
             "title": hit['_source']['title'],
             "image_name": hit['_source']['metadata']['image_name']} for hit in found_docs["hits"]["hits"]]


def execute_semantic_search(vector_store: OpenSearchVectorSearch, query: str):
    found_docs = vector_store.similarity_search_with_score(query=query, text_field="title",
                                                           vector_field="title_vector")
    return [{"score": _score,
             "title": doc.page_content,
             "image_name": doc.metadata["image_name"]} for doc, _score in found_docs]


def print_images(images: list):
    for item in images:
        st.image(image="./images/" + item['image_name'],
                 caption=item['title'],
                 width=200)

        st.write(item['score'])


if __name__ == '__main__':
    os_client, config = init_opensearch_client()
    os_search_url = f"https://{config['host']}:{config['port']}"
    lc_vectorstore = init_langchain_vectorstore(os_search_url=os_search_url)

    # Start Streamlit app
    st.set_page_config(layout="wide")
    st.title = "LEGO® BrickHeadz - Store™"

    st.header('LEGO® BrickHeadz - Store™', divider='rainbow')

    col_search, col_span, col_left, col_right = st.columns([1, 0.25, 2, 2])

    with col_search:
        st.subheader("Specify Search")
        the_query = st.text_input('What character are you looking for?', key="search_terms_input")

    with col_left:
        st.subheader("Lexical Search")

    with col_right:
        st.subheader("Semantic Search")

    if the_query:
        with col_left:
            print_images(execute_lexical_search(client=os_client, query=the_query))

        with col_right:
            print_images(execute_semantic_search(vector_store=lc_vectorstore, query=the_query))