#coding:utf-8
import json
from elasticsearch import Elasticsearch
from elasticsearch import helpers

def query_parser(query_str):
    query_str = ' %s ' % query_str.replace('AND', ' AND ').replace('OR', ' OR ').replace('NOT', ' NOT ').replace('(', '( ').replace(')', ' )')  
    keyword_str = query_str.replace('AND', '').replace('OR', '').replace('NOT', '').replace('(', '').replace(')', '')  
    keyword_list = keyword_str.split()
    for keyword in keyword_list:
        query_str = query_str.replace(' %s ' % keyword, ' \"%s\" ' % keyword)
    return query_str

def load_settings(path):
    with open(path, 'r', encoding='utf-8') as st:
        settings = json.load(st)
    return settings

def load_mappings(path):
    with open(path, 'r', encoding='utf-8') as mp:
        mappings = json.load(mp)
    return mappings

class Elastic(object):
    def __init__(self, host=[], username='', password='', timeout=480, max_retries=10, retry_on_timeout=True):
        try:
            self.es = Elasticsearch(hosts=host, http_auth=(username, password), timeout=timeout, max_retries=max_retries, retry_on_timeout=retry_on_timeout)
        except Exception as err:
            print (err)

    def create_index(self, index_name, mapping_path):
        mapping = load_mappings(mapping_path)
        self.es.indices.create(index=index_name, body=mapping, ignore=400)

    def delete_index(self, index_name):
        self.es.indices.delete(index=index_name) 

    def refresh_index(self, index_name):
        self.es.indices.refresh(index=index_name)   

    def check_index_exist(self, index_name):
        return True if self.es.indices.exists(index_name) else False

    def count(self, query, index_name):
        return self.es.count(index=index_name, body=query)['count']
        
    def gen_es_data(self, datas):
        es_data=[]
        for data in datas:
            type_name = data.pop('_type', None)
            _format= {
                '_index'  : data.pop('_index'),
                '_id'     : data.pop('_id'),
                '_routing': data.pop('_routing', None),
                '_source' : {key: value for key, value in data.items()} 
            }
            if type_name: _format['_type'] = type_name
            es_data.append(_format)
        return es_data

    def batch_load(self, datas):
        es_data = self.gen_es_data(datas)
        helpers.bulk(self.es, es_data)

    def update_data(self, datas):
        for data in datas:
            _format= {
                '_op_type': 'update',
                '_index'  : data.pop('_index'),
                '_id'     : data.pop('_id'),
                'doc'     :{key: value for key, value in data.items()} 
            }
            type_name = data.pop('_type', None)
            if type_name: _format['_type'] = type_name
            helpers.bulk(self.es, [_format])

    def delete_data(self, datas):
        for data in datas:
            _format= {
                '_op_type': 'delete',
                '_index'  : data.pop('_index'),
                '_id'     : data.pop('_id')
            }
            type_name = data.pop('_type', None)
            if type_name: _format['_type'] = type_name
            helpers.bulk(self.es, [_format])

    def scroll(self, scroll_id, scroll='2m'):
        return self.es.scroll(scroll_id=scroll_id, scroll=scroll)

    def clear_scroll(self, scroll_id):
        return self.es.clear_scroll(body={'scroll_id':scroll_id})

    def scan(self, query, index_name):
        return helpers.scan(self.es, query=query, index=index_name)

    def search(self, query, index_name, track_total_hits=False, scroll=None):
        return self.es.search(index=index_name, body=query, track_total_hits=track_total_hits, scroll=scroll)

    def msearch(self, body):
        return self.es.search(body=body)

    def search_by_id(self, index_name, type_name, _id, routing=None):
        return self.es.get(index=index_name, doc_type=type_name, id=_id, routing=routing, ignore=404)

    def search_by_ids(self, index_name, type_name, _ids):
        if _ids:
            return self.es.mget(index=index_name, doc_type=type_name, body = {'ids': _ids}, ignore=404)
        else:
            return {'docs':[]}

    def validate_query(self, body, index_name, explain=False, rewrite=False):
        return self.es.indices.validate_query(body=body, index=index_name, explain=explain, rewrite=rewrite)


class ESQuery(object):
    def __init__(self, size=None, page=None):
        self.es_query = {'query':{'bool':{}}}
        self.set_paging(page, size) 
   
    def check_query(self, query, field, type=list):
        if field not in query:
            query[field] = type()

    def get_sort_query(self, sort_by, sort_field, sort_order='desc'):
        sort_query = {
            'term': {sort_field:{'order':sort_order}},
            'field_length': {'_script':{'script':'doc[\'%s\'].size() == 0 ? 0 : doc[\'%s\'].value.replace(\' \', \'\').replace(\'\n\', \'\').length()' % (sort_field, sort_field), 'type':'number', 'order': sort_order}},
            'list_size': {'_script':{'script':'doc[\'%s\'].size()' % sort_field, 'type':'number', 'order': sort_order}}
        }
        return sort_query[sort_by]

    def set_range(self, range_field, gt=None, gte=None, lt=None, lte=None, bool_type='must'):
        range_filter = {}
        if gt is not None: 
            range_filter['gt'] = gt
        if gte is not None: 
            range_filter['gte'] = gte
        if lt is not None: 
            range_filter['lt'] = lt
        if lte is not None: 
            range_filter['lte'] = lte

        range_query = {'range':{range_field:range_filter}}
        self.check_query(self.es_query['query']['bool'], bool_type)
        self.es_query['query']['bool'][bool_type].append(range_query)

    def set_range_filter(self, range_field, gt=None, gte=None, lt=None, lte=None, bool_type='must'):
        range_filter = {}
        if gt is not None: 
            range_filter['gt'] = gt
        if gte is not None: 
            range_filter['gte'] = gte
        if lt is not None: 
            range_filter['lt'] = lt
        if lte is not None: 
            range_filter['lte'] = lte

        range_query = {'range':{range_field:range_filter}}
        self.check_query(self.es_query['query']['bool'], 'filter', type=dict)
        self.check_query(self.es_query['query']['bool']['filter'], 'bool', type=dict)
        self.check_query(self.es_query['query']['bool']['filter']['bool'], bool_type)
        self.es_query['query']['bool']['filter']['bool'][bool_type].append(range_query)

    def set_terms(self, terms, term_field, bool_type='must'):
        if terms:
            self.check_query(self.es_query['query']['bool'], bool_type)
            self.es_query['query']['bool'][bool_type].append({'terms':{term_field:terms}})

    def set_terms_filter(self, terms, term_field, bool_type='must', nested_path=None):
        if terms:
            self.check_query(self.es_query['query']['bool'], 'filter', type=dict)
            self.check_query(self.es_query['query']['bool']['filter'], 'bool', type=dict)
            self.check_query(self.es_query['query']['bool']['filter']['bool'], bool_type)
            terms_query_term = {'terms':{term_field:terms}}
            if nested_path:
                query_term = {'nested': {'path':nested_path,'query':terms_query_term}}
            else:
                query_term = terms_query_term
            self.es_query['query']['bool']['filter']['bool'][bool_type].append(query_term)

    def set_wildcard(self, term, term_field, bool_type='must'):
        if term:
            self.check_query(self.es_query['query']['bool'], bool_type)
            self.es_query['query']['bool'][bool_type].append({'wildcard':{term_field:{'value':term}}})

    def set_match_phrase(self, term, term_field, bool_type='must'):
        if term:
            self.check_query(self.es_query['query']['bool'], bool_type)
            self.es_query['query']['bool'][bool_type].append({'match_phrase':{term_field:term}})

    def set_prefix(self, term, term_field, bool_type='must'):
        if term:
            self.check_query(self.es_query['query']['bool'], bool_type)
            self.es_query['query']['bool'][bool_type].append({'prefix':{term_field:{'value':term, 'boost': 3}}})
    
    def set_match_phrase_prefix(self, term, term_field, bool_type='must'):
        if term:
            self.check_query(self.es_query['query']['bool'], bool_type)
            self.es_query['query']['bool'][bool_type].append({'match_phrase_prefix':{term_field:{'query':term}}})

    def set_match(self, text, field, analyzer, bool_type='must', nested_path=None):
        self.check_query(self.es_query['query']['bool'], bool_type)
        match_query_term = {
            'match':{
                field: {
                    'query':text, 
                    'analyzer':analyzer
                }
            }
        }
        if nested_path:
            query_term = {
                'nested': {
                    'path':nested_path,
                    'query':match_query_term
                }
            }
        else:
            query_term = match_query_term
        self.es_query['query']['bool'][bool_type].append(query_term)

    def set_keyword(self, keyword, keyword_field, bool_type='must', nested_path=None):
        if keyword:
            query_term = query_parser(keyword)
            self.check_query(self.es_query['query']['bool'], bool_type)
            qs_query_term = {
                'query_string':{
                    'query':query_term,
                    'fields':keyword_field
                }
            }
            if nested_path:
                query_term = {
                    'nested': {
                        'path':nested_path,
                        'query':qs_query_term
                    }
                }
            else:
                query_term = qs_query_term
            self.es_query['query']['bool'][bool_type].append(query_term)

    def set_minimum_should_match(self, num_of_match):
        self.es_query['query']['bool']['minimum_should_match'] = num_of_match

    def set_minimum_should_match_filter(self, num_of_match):
        self.es_query['query']['bool']['filter']['bool']['minimum_should_match'] = num_of_match

    def set_search_after(self, search_after_time):
        if search_after_time:
            self.es_query['search_after'] = search_after_time

    def set_collapse(self, field, innerhits_config={'name':None, 'page':0, 'size':10, 'sort_by':'term', 'sort_field':None, 'sort_order':'desc'}):
        self.es_query['collapse'] = {'field':field}

        if innerhits_config['name']:
            self.es_query['collapse']['inner_hits'] = {
                'name':innerhits_config['name'],
                'from':innerhits_config['page'] * innerhits_config['size'],
                'size':innerhits_config['size']
            }

            if innerhits_config['sort_field']:
                sort_query = self.get_sort_query(innerhits_config['sort_by'], innerhits_config['sort_field'], innerhits_config['sort_order'])
                self.es_query['inner_hits']['sort'] = sort_query

    def set_terms_aggs(self, agg_name, agg_field):
        if agg_field:
            self.es_query['aggs'] = {agg_name:{'terms':{'field':agg_field}}}

    def set_composite_aggs(self, agg_name, source_fields, size=10, after=None):
        source_query = []
        for source_field in source_fields:
            source_query.append({source_field:{'terms':{'field':source_field}}})

        self.es_query['aggs'] = {
            agg_name:{
                'composite':{
                    'size':size,
                    'sources':source_query
                }
            }
        }
        if after:
            self.es_query['aggs'][agg_name]['composite']['after'] = after

    def set_top_hits_aggs(self, agg_field, term_size=10000, top_hits_config={'include_fields':[], 'sort_by':'term', 'sort_field':None, 'sort_order':'desc', 'top_hits_size':1}):
        self.es_query['aggs'] = {
            agg_field:{
                'terms':{
                    'field':agg_field,
                    'size':term_size
                },
                'aggs':{
                    agg_field:{
                        'top_hits':{
                            'size':top_hits_config['top_hits_size']
                        }
                    }
                }
            }
        }
        if top_hits_config['sort_field']:
            sort_query = self.get_sort_query(top_hits_config['sort_by'], top_hits_config['sort_field'], top_hits_config['sort_order'])
            self.es_query['aggs'][agg_field]['aggs'][agg_field]['top_hits']['sort'] = [sort_query]

        if top_hits_config['include_fields']:
            self.es_query['aggs'][agg_field]['aggs'][agg_field]['top_hits']['_source']= {'includes': top_hits_config['include_fields']}

    def set_cardinality_aggs(self, agg_name, agg_field):
        self.check_query(self.es_query, 'aggs', type=dict)
        self.es_query['aggs'][agg_name] = {
            'cardinality':{
                'field': agg_field
            }
        }

    def set_field_exist(self, field, exist=True, nested=False):
        if exist:
            self.check_query(self.es_query['query']['bool'], 'must')
            self.es_query['query']['bool']['must'].append({'exists':{'field':field}} if not nested else {'nested':{'path':field,'query':{'exists':{'field':field}}}})
        elif not exist:
            self.check_query(self.es_query['query']['bool'], 'must_not')
            self.es_query['query']['bool']['must_not'].append({'exists':{'field':field}} if not nested else {'nested':{'path':field,'query':{'exists':{'field':field}}}})

    def add_explain(self):
        self.es_query['explain'] = 'true'

    def set_sort(self, sort_by, sort_field, sort_order):
        if sort_field:
            self.sort = []
            sort_query = self.get_sort_query(sort_by, sort_field, sort_order)
            self.sort.append(sort_query)
            self.es_query['sort'] = self.sort

    def add_sort(self, sort_by, sort_field, sort_order):
        if sort_field:
            sort_query = self.get_sort_query(sort_by, sort_field, sort_order)
            self.es_query['sort'].append(sort_query)

    def set_paging(self, page, size):
        if size:
            self.es_query['size'] = size
        if page:
            self.es_query['from'] = page * size

    def set_field_include(self, include_fields=[]):
        if include_fields:
            self.es_query['_source'] = include_fields

    def add_highlight(self, highlight_field, color='red', font_weight='bold'):
        self.es_query['highlight'] = {
            'tags_schema':'styled',
            'pre_tags':['<span style=\"color:%s; font-weight:%s\">' % (color, font_weight)],
            'post_tags':['</span>'],
            'fields':{}
        }
        self.es_query['highlight']['fields'] = {field:{'number_of_fragments':0} for field in highlight_field}

    def set_entity_agg(self, page, size):
        self.es_query['aggs'] = {
            'total_company_count': {
                'cardinality': {
                    'field': 'from_entity'}
            },
            'company': {
                'terms': {
                    'field': 'from_entity',
                    'size': 10000
                },
                'aggs': {
                    'company_info': {
                        'top_hits': {
                            'size': 1,
                            '_source': {
                                'includes': [
                                    'from_id',
                                    'from_entity',
                                    'from_type'
                                ]
                            }
                        }
                    },
                    'company_sort': {
                        'bucket_sort': {
                            'from': (page-1) * size,
                            'size': size
                        }
                    }
                }
            }
        }
    
