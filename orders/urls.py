from django.urls import path

from orders.views import (
    CompanyDirectoryView,
    DashboardView,
    DeliveryPdfView,
    DeliveryListView,
    DepartmentOrderView,
    OperationsHubView,
    OrderHistoryView,
    OrderThanksView,
    QrDirectoryView,
)

app_name = "orders"

urlpatterns = [
    path("", OperationsHubView.as_view(), name="operations-hub"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("delivery/", DeliveryListView.as_view(), name="delivery-list"),
    path("delivery/pdf/", DeliveryPdfView.as_view(), name="delivery-pdf"),
    path("history/", OrderHistoryView.as_view(), name="history"),
    path("companies/", CompanyDirectoryView.as_view(), name="company-directory"),
    path("qr/", QrDirectoryView.as_view(), name="qr-directory"),
    path(
        "<slug:company_slug>/<slug:department_slug>/",
        DepartmentOrderView.as_view(),
        name="department-order",
    ),
    path(
        "<slug:company_slug>/<slug:department_slug>/thanks/",
        OrderThanksView.as_view(),
        name="thanks",
    ),
]
