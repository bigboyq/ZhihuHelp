# -*- coding: utf-8 -*-
__author__ = 'yao'
import re

from baseClass import *


class ReadListParser():
    u"""
    通过Parser类，生成任务列表以及查询列表，统一存放于urlInfo中
    task结构
    *   kind
        *   task类别
            *   'answer', 'question', 'author', 'collection', 'topic', 'article', 'column', 'mixed'
    *   spider
        *   为爬虫提供信息
        *   href
            *   纯净版网址
            *   示例http://zhuanlan.zhihu.com/{}/{}".format(column_id, article_id)
            *   url尾部没有/分隔符

    *   用于在数据库中为生成epub提取数据
    *   condition
        *   sql筛选条件
        *   info
            *   提取扩展信息
        *   question
            *   提取问题列表
        *   answer
            *   用于提取答案列表
    *   sql
        *   合成后的sql
        *   info
            *   提取扩展信息
        *   question
            *   提取问题列表
        *   answer
            *   用于提取答案列表
    """
    # 先检测专栏，再检测文章，文章比专栏网址更长，类似问题与答案的关系，取信息可以用split('/')的方式获取
    supported_type_list = ['answer', 'question', 'author', 'collection', 'topic', 'article', 'column']

    # url模式
    type_pattern = {}
    type_pattern['answer'] = r'(?<=zhihu\.com/)question/(?P<question_id>\d{8})/answer/(?P<answer_id>\d{8})'
    type_pattern['question'] = r'(?<=zhihu\.com/)question/(?P<question_id>\d{8})'
    type_pattern['author'] = r'(?<=zhihu\.com/)people/(?P<author_id>[^/\n\r]*)'
    type_pattern['collection'] = r'(?<=zhihu\.com/)collection/(?P<collection_id>\d*)'
    type_pattern['topic'] = r'(?<=zhihu\.com/)topic/(?P<topic_id>\d*)'
    type_pattern['article'] = r'(?<=zhuanlan\.zhihu\.com/)(?P<column_id>[^/]*)/(?P<article_id>\d{8})'
    type_pattern['column'] = r'(?<=zhuanlan\.zhihu\.com/)(?P<column_id>[^/\n\r]*)'

    @staticmethod
    def parse_command(command):
        u"""
        用于分析指令
        """

        def remove_comment(command):
            return command.split('#')[0]

        def split_command(command):
            return command.split('$')

        command = remove_comment(command)
        command_list = split_command(command)
        task_list = []
        for command in command_list:
            task = ReadListParser.parse_command(command)
            if task:
                task_list.append(task)
        task = ReadListParser.merge_task_list(task_list)
        return task

    @staticmethod
    def init_task_package():
        u"""
        初始化最终任务列表
        """
        package = {'work_list': {}, 'question': {'info': [], 'question': '', 'answer': '', },
                   'article': {'info': [], 'question': '', 'answer': '', }}
        for task_type in ReadListParser.supported_type_list:
            package['work_list'][task_type] = []
        return package

    @staticmethod
    def merge_task_list(task_list):
        u"""
        将urlList按类别合并在一起
        """
        task_package = ReadListParser.init_task_package()
        for task in task_list:
            kind = task['kind']
            task_package['work_list'][kind].append(task['spider']['href'])
            if kind == 'article' or kind == 'column':
                task_type = 'article'
            else:
                task_type = 'question'
            task_package[task_type]['info'].append(task['condition']['info'])
            task_package[task_type]['question'].append(' ({}) '.format(task['condition']['question']))
            task_package[task_type]['answer'].append(' ({}) '.format(task['condition']['answer']))

        task_package['question']['question'] = 'select * from Question where ' + ' or '.join(
            task_package['question']['question'])
        task_package['question']['answer'] = 'select * from Answer where ' + ' or '.join(
            task_package['question']['answer'])
        task_package['article']['question'] = 'select * from ColumnInfo where ' + ' or '.join(
            task_package['article']['question'])
        task_package['article']['answer'] = 'select * from ArticleContent where ' + ' or '.join(
            task_package['article']['answer'])
        return task_package

    @staticmethod
    def parse_command(raw_command=''):
        u"""
        分析单条命令并返回待完成的task
        """

        def detect(command):
            for command_type in ReadListParser.supported_type_list:
                result = re.search(ReadListParser.type_pattern[command_type], command)
                if result:
                    return command_type
            return 'unknown'

        def parse_question(command):
            result = re.search(ReadListParser.type_pattern['question'], command)
            question_id = result.group('question_id')
            task = {}
            task['kind'] = 'question'
            task['spider'] = {}
            task['spider']['href'] = 'http://www.zhihu.com/question/{}'.format(question_id)
            task['condition'] = {}
            task['condition']['info'] = ''
            task['condition']['question'] = 'question_id = {}'.format(question_id)
            task['condition']['answer'] = 'question_id = {}'.format(question_id)
            return task

        def parse_answer(command):
            result = re.search(ReadListParser.type_pattern['answer'], command)
            question_id = result.group('question_id')
            answer_id = result.group('answer_id')
            task = {}
            task['kind'] = 'answer'
            task['spider'] = {}
            task['spider']['href'] = 'http://www.zhihu.com/question/{}/answer/{}'.format(question_id, answer_id)
            task['condition'] = {}
            task['condition']['info'] = ''
            task['condition']['question'] = 'question_id = {}'.format(question_id)
            task['condition']['answer'] = 'question_id = {} and answerID = {}'.format(question_id, answer_id)
            return task

        def parse_author(command):
            result = re.search(ReadListParser.type_pattern['author'], command)
            author_id = result.group('author_id')
            task = {}
            task['kind'] = 'author'
            task['spider'] = {}
            task['spider']['href'] = 'http://www.zhihu.com/people/{}'.format(author_id)
            task['condition'] = {}
            task['condition']['info'] = author_id
            task['condition'][
                'question'] = 'question_id in (select question_id from Answer where author_id = {})'.format(author_id)
            task['condition']['answer'] = 'author_id = {}'.format(author_id)
            return task

        def parse_collection(command):
            result = re.search(ReadListParser.type_pattern['collection'], command)
            collection_id = result.group('collection_id')
            task = {}
            task['kind'] = 'collection'
            task['spider'] = {}
            task['spider']['href'] = 'http://www.zhihu.com/collection/{}'.format(collection_id)
            task['condition'] = {}
            task['condition']['info'] = collection_id
            task['condition'][
                'question'] = 'question_id in (select question_id from Answer where href in (select href in CollectionIndex where collection_id = {}))'.format(
                collection_id)
            task['condition']['answer'] = 'href in (select href in CollectionIndex where collection_id = {})'.format(
                collection_id)
            return task

        def parse_topic(command):
            result = re.search(ReadListParser.type_pattern['topic'], command)
            topic_id = result.group('topic_id')
            task = {}
            task['kind'] = 'topic'
            task['spider'] = {}
            task['spider']['href'] = 'http://www.zhihu.com/topic/{}'.format(topic_id)
            task['condition'] = {}
            task['condition']['info'] = topic_id
            task['condition'][
                'question'] = 'question_id in (select question_id from Answer where href in (select href in TopicIndex where topic_id = {}))'.format(
                topic_id)
            task['condition']['answer'] = 'href in (select href in TopicIndex where topic_id = {})'.format(topic_id)
            return task

        def parse_article(command):
            result = re.search(ReadListParser.type_pattern['article'], command)
            column_id = result.group('column_id')
            article_id = result.group('article_id')
            task = {}
            task['kind'] = 'article'
            task['spider'] = {}
            task['spider']['href'] = 'http://zhuanlan.zhihu.com/{}/{}'.format(column_id, article_id)
            task['condition'] = {}
            task['condition']['info'] = column_id
            task['condition']['question'] = 'columnID = {} and articleID = {}'.format(column_id, article_id)
            task['condition']['answer'] = 'columnID = {} and articleID = {}'.format(column_id, article_id)
            return task

        def parse_column(command):
            result = re.search(ReadListParser.type_pattern['column'], command)
            column_id = result.group('column_id')
            task = {}
            task['kind'] = 'article'
            task['spider'] = {}
            task['spider']['href'] = 'http://zhuanlan.zhihu.com/{}/{}'.format(column_id, article_id)
            task['condition'] = {}
            task['condition']['info'] = column_id
            task['condition']['question'] = 'columnID = {} and articleID = {}'.format(column_id, article_id)
            task['condition']['answer'] = 'columnID = {} and articleID = {}'.format(column_id, article_id)
            return task

        def parse_error(command):
            BaseClass.logger.info(u"""匹配失败，未知readList类型。\n失败命令:{}""".format(command))
            return

        parser = {'answer': parse_answer, 'question': parse_question, 'author': parse_author,
                  'collection': parse_collection, 'topic': parse_topic, 'article': parse_article,
                  'column': parse_column, 'unknown': parse_error, }
        kind = detect(raw_command)
        return parser[kind](raw_command)
