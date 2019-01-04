# -*- coding: UTF-8 -*-

import pymysql
from scrapy.utils.project import get_project_settings  # 导入seetings配置


class DBHelper():

    def __init__(self):
        # self.settings = get_project_settings()  # 获取settings配置，设置需要的信息
        # Mysql数据库的配置信息
        self.settings={}
        self.settings['MYSQL_HOST'] = 'localhost'
        self.settings['MYSQL_DBNAME'] = 'audio'  # 数据库名字，请修改
        self.settings['MYSQL_USER'] = 'root'  # 数据库账号，请修改
        self.settings['MYSQL_PASSWD'] = '12358'  # 数据库密码，请修改
        self.settings['MYSQL_PORT'] = 3307  # 数据库端口，在dbhelper中使用

        self.host = self.settings['MYSQL_HOST']
        self.port = self.settings['MYSQL_PORT']
        self.user = self.settings['MYSQL_USER']
        self.passwd = self.settings['MYSQL_PASSWD']
        self.db = self.settings['MYSQL_DBNAME']

    # 连接到mysql，不是连接到具体的数据库
    def connectMysql(self):
        conn =pymysql.connect(host=self.host,
                               port=self.port,
                               user=self.user,
                               passwd=self.passwd,
                               # db=self.db,不指定数据库名
                               charset='utf8')  # 要指定编码，否则中文可能乱码
        return conn

    # 连接到具体的数据库（settings中设置的MYSQL_DBNAME）
    def connectDatabase(self):
        conn =pymysql.connect(host=self.host,
                               port=self.port,
                               user=self.user,
                               passwd=self.passwd,
                               db=self.db,
                               charset='utf8')  # 要指定编码，否则中文可能乱码
        return conn

        # 创建数据库

    def createDatabase(self):

        conn = self.connectMysql()  # 连接数据库
        sql = "create database if not exists " + self.db
        cur = conn.cursor()
        cur.execute(sql)  # 执行sql语句
        cur.close()
        conn.close()

    # 创建表
    def createTable(self, sql):
        conn = self.connectDatabase()
        cur = conn.cursor()
        cur.execute(sql)
        cur.close()
        conn.close()

    # 插入数据
    def insert(self, sql, *params):
        conn = self.connectDatabase()
        cur = conn.cursor();
        cur.execute(sql, params)
        conn.commit()
        cur.close()
        conn.close()

    # 更新数据
    def update(self, sql, *params):
        conn = self.connectDatabase()
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
        conn.close()

    # 删除数据
    def delete(self, sql, *params):
        conn = self.connectDatabase()
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        cur.close()
        conn.close()


'''测试DBHelper的类'''


class TestDBHelper():
    def __init__(self):
        self.dbHelper = DBHelper()

    # 测试创建数据库）
    def testCreateDatebase(self):
        self.dbHelper.createDatabase()
        # 测试创建表

    def testCreateTable(self):
        sql = "create table path(id int primary key auto_increment,AUDIO_URL varchar(200),JSON_URL varchar(200))"
        self.dbHelper.createTable(sql)

    # 测试插入
    def testInsert(self,audio_url,json_url):
        sql = "insert into path(AUDIO_URL,JSON_URL) values(%s,%s)"
        params = (audio_url, json_url)
        self.dbHelper.insert(sql, *params)

    def testUpdate(self):
        sql = "update path set AUDIO_URL=%s,JSON_URL=%s where id=%s"
        params = ("update", "update", "1")
        self.dbHelper.update(sql, *params)

    def testDelete(self):
        sql = "delete from path where id=%s"
        params = ("1")
        self.dbHelper.delete(sql, *params)


if __name__ == "__main__":
    testDBHelper = TestDBHelper()
   # testDBHelper.testCreateDatebase()  #执行测试创建数据库
    testDBHelper.testCreateTable()     #执行测试创建表
    #testDBHelper.testInsert()          #执行测试插入数据
    #testDBHelper.testUpdate()          #执行测试更新数据
    #testDBHelper.testDelete()          #执行测试删除数据
