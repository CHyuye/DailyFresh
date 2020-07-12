from apps.goods.models import GoodsSKU  # 导入模型类
from haystack import indexes  # 定义索引类


# 指定对应某个类的某些数据建立索引
# 索引类名的格式：模型类名+Index
class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
    # 索引字段，use_tempalte=True指定根据表中哪些字段建立索引文件说明放在那个文件中
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        # 返回你的模型类
        return GoodsSKU

    # 建立索引数据
    def index_queryset(self, using=None):
        return self.get_model().objects.all()
