from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from apps.goods.models import GoodsSKU
from django_redis import get_redis_connection
from utils.mixin import LoginRequestMixin

# Create your views here.
"""
添加商品到购物车：
1）请求方式：采用ajax， post
如果涉及到数据的增删改查，采用post
2）如果只涉及到数据的获取，采用get
3）传递参数：商品id(sku_id), 商品数量(count)
"""


# /cart/add
class CartAddView(View):
    """购物车记录添加"""
    def post(self, request):
        """购物车商品的添加"""
        user = request.user
        # 判断用户是否登录
        if not user.is_authenticated:
            # 用户未登录
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})

        # 接收数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 校验数据
        if not all([sku_id, count]):
            # 数据不完整
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 检验添加的商品数目
        try:
            count = int(count)
        except Exception as e:
            # 商品数目出错
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})

        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 业务处理：购物车添加
        # 链接redis数据库进行添加或查询已有添加
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # 先尝试获取sku_id的值，--> hget cart_key 属性
        cart_count = conn.hget(cart_key, sku_id)
        # 如果sku_id在hash中不存在则返回None
        if cart_count:
            # 累加购物车中的数目
            count += int(cart_count)

        # 校验商品的库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        # 设置hash中sku_id对应的值
        # hash --> 如果sku_id已经存在，更新数据，不存在进行添加
        conn.hset(cart_key, sku_id, count)

        # 计算用户购物车商品的条目
        total_count = conn.hlen(cart_key)

        # 返回应答
        return JsonResponse({'res': 5, 'total_count': total_count, 'message': '添加成功'})


class CartInfoView(LoginRequestMixin, View):
    """购物车页面显示"""
    def get(self, request):
        """购物车显示"""
        # 获取登录的用户
        user = request.user
        # 获取用户购物车中的商品信息
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # {'商品id':商品数目}
        cart_dict = conn.hgetall(cart_key)

        skus = []
        total_price = 0
        total_count = 0
        # 遍历获取商品的信息
        for sku_id, count in cart_dict.items():
            # 根据商品的id获取商品信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 计算商品的小计
            amount = sku.price*int(count)
            # 动态给sku对象添加amount属性，保存商品小计
            sku.amount = amount
            # 动态给sku指定count属性，保存购物车数量
            sku.count = int(count)
            # 添加
            skus.append(sku)

            # 累加计算商品的总数目和总价钱
            total_count += int(count)
            total_price += amount

        # 组织上下文
        context = {
            'total_count': total_count,
            'total_price': total_price,
            'skus': skus
        }

        # 传递参数，返回应答
        return render(request, 'cart.html', context)


"""
    更新购物车信息
    采用ajax post 请求
    前端需要传递的信息，商品id(sku_id) 更新商品数目(count)
"""


# /cart/update
class CartUpdateView(View):
    """购物车信息更新"""
    def post(self, request):
        # 用户登录信息
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 校验数据
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验添加的商品数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品数量出错'})

        # 检验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 业务处理：更新记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        # 判断库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        #  更新记录
        conn.hset(cart_key, sku_id, count)

        # 统计商品的总件数{'1':5, '2':3} 8件
        values = conn.hvals(cart_key)
        total_count = 0
        for value in values:
            total_count += int(value)

        # 返回应答
        return JsonResponse({'res': 5, 'total_count': total_count, 'message': '更新成功'})


"""
    前端删除购物车记录
    采用ajax post请求
    前端传递参数：商品id
"""
# /cart/delete
class CartDeleteView(View):
    """购物车记录删除"""
    def post(self, request):
        # 用户登录信息
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        sku_id = request.POST.get('sku_id')

        #  数据的校验
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的商品'})

        # 检验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        # 业务处理：商品记录删除
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # 删除 hdel
        conn.hdel(cart_key, sku_id)

        # 计算商品的总件数
        values = conn.hvals(cart_key)
        total_count = 0
        for value in values:
            total_count += int(value)

        # 返回应答
        return JsonResponse({'res': 3, 'total_count': total_count, 'message': '删除成功'})

