from django.shortcuts import render, redirect, reverse
from django.views.generic import View
from apps.goods.models import GoodsType, GoodsSKU, IndexGoodsBanner, IndexTypeGoodsBanner, IndexPromotionBanner
from django_redis import get_redis_connection
from django.core.cache import cache
from django.core.paginator import Paginator
from apps.order.models import OrderGoods


# Create your views here.
class IndexView(View):
    """首页"""
    def get(self, request):
        """显示首页"""
        # 尝试从缓存中读数据
        context = cache.get('index_page_data')

        if context is None:
            # 获取商品种类信息
            types = GoodsType.objects.all()

            # 获取首页轮播商品信息
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')

            # 获取首页促销商品信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            # 获取首页分类商品展示信息
            for type in types:  # GoodsType
                # 获取type种类首页分类商品的图片展示信息
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
                # 获取type种类首页分类商品的文字展示信息
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
                # 动态给type增加属性，分别给增加首页分类商品的图片展示信息和文字展示信息
                type.image_banners = image_banners
                type.title_banners = title_banners

            context = {
                'types': types,
                'goods_banners': goods_banners,
                'promotion_banners': promotion_banners
            }

            # 设置缓存
            # key value timeout
            # cache.set('index_page_data', context, 3600)

        # 获取用户购物车上的的数目信息
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        # 组织模板上下文
        context.update(cart_count=cart_count)

        return render(request, 'index.html', context)


class DetailView(View):
    """详情页"""
    def get(self, request, goods_id):
        """显示详情页"""
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在时，跳转到首页
            return redirect(reverse('goods:index'))

        # 获取商品的分类信息
        types = GoodsType.objects.all()

        # 获取商品评论信息
        sku_comment = OrderGoods.objects.filter(sku=sku).exclude(comment='')

        # 获取新品信息
        sku_new = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]

        # 获取同一SPU的其他规格的商品
        same_spu_sku = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        # 获取用户购物车上的的数目信息
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            # 用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

            # 添加用户历史浏览记录
            conn = get_redis_connection('default')
            history_key = 'history_%d' % user.id
            # 移除列表中的goods_id
            conn.lrem(history_key, 0, goods_id)
            # 把goods_id从左侧添加
            conn.lpush(history_key, goods_id)
            # 只保存用户最新浏览的5条记录
            conn.ltrim(history_key, 0, 4)

        # 组织模板上下文
        context = {
            'sku': sku, 'types': types,
            'sku_comment': sku_comment,
            'sku_new': sku_new,
            'same_spu_sku': same_spu_sku,
            'cart_count': cart_count
        }
        # 使用模板
        return render(request, 'detail.html', context)


# 种类id 页码 排序方式
# /list/type_id=种类id&page=页码&sort=排序方式
# /list/种类id/页码/排序方式
# /list/种类id/页码?sort=排序方式
class ListView(View):
    def get(self, request, type_id, page):
        """显示列表页"""
        # 获取种类信息
        try:
            type = GoodsType.objects.get(id=type_id)
        except Exception as e:
            # 种类不存在
            return redirect(reverse('goods:index'))
        # 获取商品分类信息
        types = GoodsType.objects.all()

        # 获取排序的方式
        # sort=default， 按照默认的id排序
        # sort=price，按照价格排序
        # sort=hot，按照销量排序
        sort = request.GET.get('sort')
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')

        # 对数据进行分页
        paginator = Paginator(skus, 1)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取第page页的Paginator的实例对象
        sku_page = paginator.page(page)

        # 1、总页数小于5时，显示所有页码
        # 2、如果当前页在前3页，显示前5页的页码
        # 3、如果当前页在后3页，显示后5页的页码
        # 4、其他情况：显示前2页，当前页后2页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages+1)
        elif num_pages <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages-4, num_pages+1)
        else:
            pages = range(page-2, page+3)

        # 获取新品信息
        new_sku = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        # 获取购物车商品数目
        user = request.GET.get('user')
        cart_count = 0
        if user.is_authenticated:
            # 用户已登录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        # 组织模板上下文
        context = {
            'types': types, 'type': 'type',
            'new_sku': new_sku,
            'cart_count': cart_count,
            'sku_page': sku_page,
            'sort': sort, 'page': pages
        }

        # 使用模板文件
        return render(request, 'list.html', context)
