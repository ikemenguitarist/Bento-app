from datetime import date

from django.contrib import messages
from django.http import FileResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View

from orders.services import (
    build_delivery_pdf,
    get_company_directory_context,
    get_dashboard_context,
    get_department_or_404,
    get_delivery_list_context,
    get_order_history_context,
    get_order_form_context,
    get_qr_directory_context,
    parse_quantities,
    submit_order,
)


def parse_date_query(request, *, default_to_today):
    raw_value = request.GET.get("date", "").strip()
    if not raw_value:
        if default_to_today:
            today = timezone.localdate()
            return today, today.isoformat()
        return None, ""

    try:
        parsed = date.fromisoformat(raw_value)
    except ValueError:
        messages.error(request, "日付は YYYY-MM-DD 形式で指定してください。")
        if default_to_today:
            today = timezone.localdate()
            return today, today.isoformat()
        return None, ""

    return parsed, raw_value


class DepartmentOrderView(View):
    template_name = "orders/order_form.html"

    def get(self, request, company_slug, department_slug):
        context = get_order_form_context(company_slug, department_slug)
        return render(request, self.template_name, context)

    def post(self, request, company_slug, department_slug):
        context = get_order_form_context(company_slug, department_slug)
        department = get_department_or_404(company_slug, department_slug)
        menus = [row["menu"] for row in context["menu_rows"]]
        quantities, errors = parse_quantities(request.POST, menus)

        if context["deadline"]["passed"]:
            messages.error(request, "締切を過ぎているため、注文を更新できません。")
            return render(request, self.template_name, context, status=400)

        if errors:
            valid_quantities = {menu.id: qty for menu, qty in quantities.items()}
            context["menu_rows"] = [
                {
                    "menu": row["menu"],
                    "quantity": valid_quantities.get(row["menu"].id, 0),
                }
                for row in context["menu_rows"]
            ]
            context["errors"] = errors
            return render(request, self.template_name, context, status=400)

        try:
            submit_order(department, quantities)
        except ValueError as exc:
            messages.error(request, str(exc))
            return render(request, self.template_name, context, status=400)

        return redirect(
            "orders:thanks",
            company_slug=company_slug,
            department_slug=department_slug,
        )


class OrderThanksView(View):
    template_name = "orders/thanks.html"

    def get(self, request, company_slug, department_slug):
        department = get_department_or_404(company_slug, department_slug)
        context = {
            "company": department.company,
            "department": department,
        }
        return render(request, self.template_name, context)


class DashboardView(View):
    template_name = "orders/dashboard.html"

    def get(self, request):
        target_date, selected_date = parse_date_query(request, default_to_today=True)
        context = get_dashboard_context(target_date=target_date)
        context["selected_date"] = selected_date
        return render(request, self.template_name, context)


class DeliveryListView(View):
    template_name = "orders/delivery_list.html"

    def get(self, request):
        target_date, selected_date = parse_date_query(request, default_to_today=True)
        context = get_delivery_list_context(target_date=target_date)
        context["selected_date"] = selected_date
        return render(request, self.template_name, context)


class DeliveryPdfView(View):
    def get(self, request):
        target_date, _ = parse_date_query(request, default_to_today=True)
        pdf_file = build_delivery_pdf(target_date=target_date)
        filename = f"delivery_list_{target_date.isoformat()}.pdf"
        return FileResponse(pdf_file, as_attachment=True, filename=filename)


class OrderHistoryView(View):
    template_name = "orders/history.html"

    def get(self, request):
        target_date, selected_date = parse_date_query(request, default_to_today=False)
        context = get_order_history_context(target_date=target_date)
        context["selected_date"] = selected_date
        return render(request, self.template_name, context)


class CompanyDirectoryView(View):
    template_name = "orders/company_directory.html"

    def get(self, request):
        context = get_company_directory_context(request.build_absolute_uri("/orders/"))
        return render(request, self.template_name, context)


class QrDirectoryView(View):
    template_name = "orders/qr_directory.html"

    def get(self, request):
        context = get_qr_directory_context(request.build_absolute_uri("/orders/"))
        return render(request, self.template_name, context)


class OperationsHubView(View):
    template_name = "orders/operations_hub.html"

    def get(self, request):
        today = timezone.localdate().isoformat()
        context = {
            "sections": [
                {
                    "title": "日次運用",
                    "description": "当日の注文確認、配送準備、履歴確認を行います。",
                    "links": [
                        {
                            "label": "当日ダッシュボード",
                            "url": f'{reverse("orders:dashboard")}?date={today}',
                        },
                        {
                            "label": "配送リスト",
                            "url": f'{reverse("orders:delivery-list")}?date={today}',
                        },
                        {
                            "label": "配送リストPDF",
                            "url": f'{reverse("orders:delivery-pdf")}?date={today}',
                        },
                        {
                            "label": "注文履歴",
                            "url": reverse("orders:history"),
                        },
                    ],
                },
                {
                    "title": "配布と案内",
                    "description": "企業・部署ごとの注文URLやQRコードを配布します。",
                    "links": [
                        {
                            "label": "企業・部署一覧",
                            "url": reverse("orders:company-directory"),
                        },
                        {
                            "label": "QR一覧",
                            "url": reverse("orders:qr-directory"),
                        },
                    ],
                },
                {
                    "title": "マスタ管理",
                    "description": "企業、部署、メニュー、締切設定を Django admin で更新します。",
                    "links": [
                        {
                            "label": "企業管理",
                            "url": reverse("admin:companies_company_changelist"),
                        },
                        {
                            "label": "部署管理",
                            "url": reverse("admin:companies_department_changelist"),
                        },
                        {
                            "label": "メニュー管理",
                            "url": reverse("admin:menus_menu_changelist"),
                        },
                        {
                            "label": "締切設定",
                            "url": reverse("admin:core_orderdeadlinesetting_changelist"),
                        },
                    ],
                },
            ]
        }
        return render(request, self.template_name, context)
