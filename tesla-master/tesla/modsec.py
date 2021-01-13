#!/usr/bin/python
# -*- coding: utf-8 -*-

import argparse
import datetime
import json
import os
import re
import shutil
import time
import zipfile
from elasticsearch import Elasticsearch
import actionslog as log

__author__ = "Cristian Souza <cristianmsbr@gmail.com>"
__copyright__ = "Copyright 2018, Actions Security"

class ModSecurityParser():
	def __init__(self, host, port, user, secret):
		self.es = Elasticsearch([host + ':' + str(port)], http_auth = (user, secret))
		self.descriptions_file = open("tesla/descriptions.txt", "r").readlines()

		self.dir_count = 0
		self.file_count = 0
		self.zip_path = None
		self.backup_path = os.path.expanduser("~") + "/modsec_logs_backup/"

		self.today = datetime.datetime.now().strftime("%Y/%m/%d")

	def send(self, path_to_directory):
		print("[!] Searching for files...")
		self.zip_path = self.backup_path + str(datetime.datetime.now()) + ".zip"

		file_obj = open(path_to_directory + "/modsecurity.log", "r")
		text = file_obj.read()

		if (len(text) > 0):
			for item in text.split("\n"):
				if ("ModSecurity" in item):
					data = self.parse(item)

					if (data is not None):
						self.send_to_elasticsearch(data)
						self.make_backup(path_to_directory)

			print("[*] File {} sent!".format(path_to_directory + "/modsecurity.log"))

		file_obj.close()

	def parse(self, item):
		items = {}

		line = item.strip()
		start_msg_modsec = line.find("ModSecurity:")
		end_msg_modesec = line.find("[file")
		line_without_msg = line[:start_msg_modsec] + line[end_msg_modesec:]
		split = re.findall("\[.*?\]", line_without_msg)

		if ("[\\d.:]" in split):
			split.remove("[\\d.:]")

		for item in split:
			item = item.replace("[", "")
			item = item.replace("]", "")

			tag = item.split(" ")
			tag_name = tag[0]

			item = re.findall(r'"([^"]*)"', item)
			try:
				if (item[0] is not None):
					items[tag_name] = item[0]
			except:
				pass

		print(items)

		for line in self.descriptions_file:
			line = line.split("|")
			if (line[0] in items["file"]):
				items["type"] = line[1]

		items["backup"] = self.zip_path
		items["date"] = self.today

		return json.dumps(items)

	def send_to_elasticsearch(self, data):
		self.es.index(index = "modsecurity_logs", doc_type = "modsecurity", body = data)

	def make_backup(self, path):
		if not os.path.exists(self.backup_path):
			os.makedirs(self.backup_path)

		self.zip_file = zipfile.ZipFile(self.zip_path, "w", zipfile.ZIP_DEFLATED)

		for root, dirs, files in os.walk(path):
			for file in files:
				self.zip_file.write(os.path.join(root, file))
				open(os.path.join(root, file), 'w').close() # truncate

		self.zip_file.close()
		print("[!] Backup done, file saved in: " + self.zip_path)
