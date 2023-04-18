import os
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import pickle
import json
from src.sdcounty import *

tmp_dir = os.getcwd()
parent_dir = os.path.dirname(tmp_dir)
data_path = os.path.join(tmp_dir,'San Diego County','data')
run_update(data_path)