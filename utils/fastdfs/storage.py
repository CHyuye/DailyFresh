from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from django.conf import settings


class FastDFSStorage(Storage):
    """fast dfs文件存储类"""
    def __init__(self, client_conf=None, base_url=None):
        """
        初始化——进行判断，如果没有传入相应的信息，就使用默认的
        client_conf:设置FastDFS使用的client.conf文件路径
        base_url:设置FastDFS的存储服务器上的nginx的ip和端口号
        """
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if base_url is None:
            base_url = settings.FDFS_URL
        self.base_url = base_url

    def _open(self, name, mode='rb'):
        """此处用不到打开文件，故省略"""
        pass

    def _save(self, name, content):
        """
        在fastDFS中保存文件
        :param name: 传入的文件名
        :param content: 文件内容
        :return: 保存到数据库中的FastDFS的文件名
        """
        # 创建一个Fdfs_client对象
        client = Fdfs_client(self.client_conf)

        # 上传文件到fast dfs系统中
        res = client.upload_appender_by_buffer(content.read())

        """
        return dict {
            'Group name'      : group_name,
            'Remote file_id'  : remote_file_id,
            'Status'          : 'Upload successed.',
            'Local file name' : '',
            'Uploaded size'   : upload_size,
            'Storage IP'      : storage_ip
        }
        """
        if res.get('Status') != 'Upload successed.':
            # 上传失败
            raise Exception('上传文件到Fast DFS 失败！')

        # 获取返回的文件id
        filename = res.get('Remote file_id')
        return filename

    def exists(self, name):
        """
        判断文件是否存在，FastDFS可以自行解决文件的重名问题
        所以此处返回False，告诉Django上传的文件都是新文件
        :param name: 文件名
        :return: False
        """
        return False

    def url(self, name):
        """返回访问文件的url路径"""
        return self.base_url + name
