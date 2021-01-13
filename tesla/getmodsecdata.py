import json
import requests
from elasticsearch import Elasticsearch

es = Elasticsearch("http://elastic:lz6i7SbJ4ATe35WK2kV@150.165.202.190:9200")
r = requests.get("http://elastic:lz6i7SbJ4ATe35WK2kV@150.165.202.190:9200")

print(r.content + "\n\n")
print(es.get(index = "modsecurity_logs", id = "AWbK-JKZHhmQl6hg1UlH", doc_type = "modsecurity"))
