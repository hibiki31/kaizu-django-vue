from django.db.models.expressions import Subquery
from wallets.models import Wallet
from django_filters import rest_framework as filters
from django.core import serializers
from django.db import connection, transaction, models
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.response import Response
import json
from .models import Transaction, Supplier
from items.models import Item, Category, SubCategory
from .serializers import TransactionSerializer, SupplierSerializer
import csv
import io
from datetime import datetime


class SupplierFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr='contains')

    class Meta:
        model = Supplier
        fields = ['name']


class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer

    def get_queryset(self):
        queryset = Transaction.objects.order_by('date','pk').reverse().all()
        if (name := self.request.query_params.get('name')) is not None:
            queryset = queryset.filter(items__name__icontains=name)
        if (supplier := self.request.query_params.get('supplier')) is not None:
            queryset = queryset.filter(supplier__name__icontains=supplier)
        if (category := self.request.query_params.get('category')) is not None:
            queryset = queryset.filter(items__sub_category__category__pk=category)
        if (subcategory := self.request.query_params.get('subcategory')) is not None:
            queryset = queryset.filter(items__sub_category__pk=subcategory)
        if (wallet := self.request.query_params.get('wallet')) is not None:
            queryset = queryset.filter(Q(wallet_income=wallet) | Q(wallet_expenses=wallet))
        if (kind := self.request.query_params.get('kind')) is not None:
            queryset = queryset.filter(kind=kind)
        if (year := self.request.query_params.get('year')) is not None:
            queryset = queryset.filter(date__year=year)
        if (month := self.request.query_params.get('month')) is not None:
            queryset = queryset.filter(date__month=month)
        return queryset


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    pagination_class = None
    filter_class = SupplierFilter


class CategorySummaryView(APIView):
    def get(self, request, format=None):
        
        transaction = Item.objects.filter(
                transaction__date__year=request.query_params.get('year','2021')
            ).values(
            month=models.F('transaction__date__month'),
            category_name=models.F('sub_category__category__name'), 
            category_id=models.F('sub_category__category__pk')
            ).annotate(
                amount=models.Sum('amount_expenses')
            ).all()
        
        sum_dict = {}

        for i in transaction:
            if not i['category_id'] in sum_dict:
                sum_dict[i['category_id']] = {}
            sum_dict[i['category_id']][i['month']] = i["amount"]

        
        category = Category.objects.all()

        result_list = []
        for i in category:
            summary = []
            for j in range(1, 12 + 1):
                try:
                    amount = sum_dict[i.pk][j]
                except:
                    amount = 0
                summary.append(amount)
            row = {
                    "name": i.name,
                    "pk": i.pk,
                    "color": i.color,
                    "summary": summary
            }
            result_list.append(row)
        
        return Response(result_list)
        return Response(json.loads(serializers.serialize('json', transaction)))

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

@csrf_exempt
def rakuten_card_csv(request):
    if request.method == 'POST':
        data = io.TextIOWrapper(request.FILES['file'].file, encoding='utf-8')
        csv_content = list(csv.reader(data))

        print(request.POST.get('type', None))

        if ['\ufeff"利用日"', '利用店名・商品名', '利用者', '支払方法', '利用金額', '支払手数料', '支払総額', '9月支払金額', '10月繰越残高', '新規サイン'] != csv_content[0]:
            return HttpResponse({"error"})
        for i in csv_content:
            print(i)
            if i[0] == '\ufeff"利用日"' or i[0] == '':
                continue
            
            transaction = Transaction(
                date = datetime.strptime(i[0], "%Y/%m/%d"),
                wallet_income = Wallet(pk=int(request.POST.get('wallet', None))),
                wallet_expenses = Wallet(pk=int(request.POST.get('wallet', None))),
                supplier = Supplier(pk=int(request.POST.get('supplier', None)))
            )
            transaction.save()
            item = Item(
                name = i[1],
                amount_income = 0,
                amount_expenses = int(i[7]),
                transaction = transaction,
                sub_category = SubCategory(pk=int(request.POST.get('subcategory', None)))
            )
            item.save()
    
    return HttpResponse({"success"})