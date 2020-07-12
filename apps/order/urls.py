from django.urls import path, re_path
from apps.order.views import OrderPlaceView, OrderCommitView, OrderPayView, CheckPayView, CommentView

urlpatterns = [
    path('place', OrderPlaceView.as_view(), name='place'),  # 提交订单
    path('commit', OrderCommitView.as_view(), name='commit'),  # 订单创建
    path('pay', OrderPayView.as_view(), name='pay'),  # 订单支付
    path('check', CheckPayView.as_view(), name='check'),  # 查询订单结果
    re_path(r'^comment/(?P<order_id>\d+)$', CommentView.as_view(), name='comment')  # 评论
]