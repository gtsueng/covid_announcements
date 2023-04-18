import os
import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import pickle
import json


#### Functions for getting archived url lists
def get_page_links(article_main_object):
    linklist = []
    articlelist = article_main_object.findAll("article")
    for eacharticle in articlelist:
        headerobject = eacharticle.findAll('h2', class_='entry-title card-title')
        postlink = headerobject[0].findAll('a')
        linklist.append(postlink[0].get("href"))
    return(linklist)


def get_lastpage(article_main_object):
    pageobject = article_main_object.findAll('div', class_='pagination')
    lastpage = pageobject[0].findAll('a', class_='page-numbers')[-2].contents[1]
    return(lastpage)


def get_archive_links(baseurl,daterange):
    archivelinks = []
    for eachdate in daterange:
        rawresult = requests.get(baseurl+eachdate)
        archivemain = BeautifulSoup(rawresult.text, "html.parser")
        archivelinks.extend(get_page_links(archivemain))
        lastpage = get_lastpage(archivemain)
        i=2
        while i < int(lastpage)+1:
            rtmp = requests.get(baseurl+eachdate+'page/'+str(i)+'/')
            tmpresult = BeautifulSoup(rtmp.text, "html.parser")
            archivelinks.extend(get_page_links(tmpresult))
            i=i+1
            time.sleep(0.5)
    return(archivelinks)



#### Functions for getting article content
def get_authors(mainarticle):
    authors = []
    authorlist = mainarticle.findAll("span",class_="author vcard")
    for eachauthor in authorlist:
        basic_author = eachauthor.text.split(', ')
        authorname = basic_author[0]
        affiliation = basic_author[-1]
        nameparts = authorname.split(" ")
        tmpdict = {'type':'@Person','name':authorname,'affiliation':{'name':affiliation}}
        if len(nameparts)==3:
            tmpdict['givenName'] = nameparts[0]+' '+nameparts[1]
            tmpdict['familyName'] = nameparts[2]
        elif len(nameparts)==2:
            tmpdict['givenName'] = nameparts[0]
            tmpdict['familyName'] = nameparts[1]
        authors.append(tmpdict)
    return(authors)


def get_keywords(mainarticle):
    keywordprops = mainarticle.findAll("meta",{"property":"article:tag"})
    keywords = []
    for eachentry in keywordprops:
        keywords.append(eachentry.get("content"))
    return(keywords)


def get_basic_info(mainarticle):
    article_title = mainarticle.find("meta",{"property":"og:title"}).get("content")
    article_description = mainarticle.find("meta",{"property":"og:description"}).get("content")
    try:
        datePublished = mainarticle.find("meta",{"property":"article:published_time"}).get("content")
    except:
        datePublished = mainarticle.find("meta",{"property":"og:updated_time"}).get("content")
    try:
        dateModified = mainarticle.find("meta",{"property":"article:modified_time"}).get("content")
    except:
        dateModified = mainarticle.find("meta",{"property":"og:updated_time"}).get("content")
    url = mainarticle.find("meta",{"property":"og:url"}).get("content")
    authors = get_authors(mainarticle)
    keywords = get_keywords(mainarticle)
    tmpdict = {'name':article_title,'description':article_description,'datePublished':datePublished,
               'url':url,'keywords':keywords, 'author':authors, 'dateModified':dateModified}
    return(tmpdict)


def get_other_meta(mainarticle):
    articletype = mainarticle.find("meta",{"property":"og:type"}).get("content")
    article = mainarticle.find("div",class_="entry-content").text
    return({"articleType":articletype,"articleContent":article})



## Functions for getting new posts
def get_update_urls():
    newsfeed = feedparser.parse("https://www.countynewscenter.com/news/rss")
    newsresults=[]
    for eachentry in newsfeed.entries:
        newsresults.append(eachentry['id'])
    return(newsresults)


## Functions for parsing results
def parse_page(linklist,data_path):
    failures = []
    baseurl = 'https://www.countynewscenter.com/'
    location = {"name":"San Diego County","_id":"USA_US-CA_06073"}
    context = {
    "@type": "SpecialAnnouncement",
    "@context": {
        "schema": "http://schema.org/",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "bts": "http://schema.biothings.io/",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "owl": "http://www.w3.org/2002/07/owl/",
        "niaid": "https://discovery.biothings.io/view/niaid/",
        "outbreak": "https://discovery.biothings.io/view/outbreak/"
      }
    }
    for eachlink in linklist:
        try:
            rawresult = requests.get(eachlink)
            mainarticle = BeautifulSoup(rawresult.text, "html.parser")
            basicdict = context.copy()
            basicdict.update(get_basic_info(mainarticle))
            basicdict.update(get_other_meta(mainarticle))
            basicdict['location']=location
            timestring = basicdict['datePublished'].split('T')[1].split('-')[0]
            datestring = basicdict['datePublished'].split('T')[0]
            basicdict['_id'] = basicdict['location']["_id"].replace('-','.')+'_'+datestring.replace('-','')+'.'+timestring.replace(':','.')
            filename = basicdict['_id']+'.json'
            with open(os.path.join(data_path,'archive',filename), 'w') as json_file:
                json.dump(basicdict, json_file)
        except:
            failures.append(eachlink)
        time.sleep(0.5)
    return(failures)


#### Functions for getting most recent 10 results
def run_update(data_path):
    new_results = get_update_urls()     ## Get new urls
    archivedlinks = pickle.load(open(os.path.join(data_path,'link_list.txt'),"rb")) ## Load previous urls
    new_urls = [x for x in new_results if x not in archivedlinks] ## Check if they've been run before
    parse_page(new_urls,data_path) ## Process the new urls
    ## update previous list
    all_links = new_urls + archivedlinks 
    with open(os.path.join(data_path,'link_list.txt'),"wb") as dmpfile:
        pickle.dump(all_links, dmpfile)    
        

#### Main
tmp_dir = os.getcwd()
parent_dir = os.path.dirname(tmp_dir)
data_path = os.path.join(tmp_dir,'San Diego County','data')
run_update(data_path)
