import base64
from datetime import datetime, time, timedelta
from io import BytesIO

import qrcode
from django.db import transaction
from django.db.models import Prefetch, Sum
from django.http import Http404
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

from companies.models import Company, Department
from core.models import OrderDeadlineSetting
from menus.models import Menu
from orders.models import Order, OrderItem, OrderStatus

DEFAULT_ORDER_DEADLINE = time(hour=9, minute=30)


def get_order_deadline(target_date=None):
    if target_date is None:
        target_date = timezone.localdate()

    setting = (
        OrderDeadlineSetting.objects.filter(
            is_active=True,
            applies_from__lte=target_date,
        )
        .order_by("-applies_from", "-id")
        .first()
    )
    return setting.order_deadline_time if setting else DEFAULT_ORDER_DEADLINE


def get_deadline_status(target_date=None):
    if target_date is None:
        target_date = timezone.localdate()

    current_dt = timezone.localtime()
    deadline = get_order_deadline(target_date)
    deadline_dt = timezone.make_aware(
        datetime.combine(target_date, deadline),
        timezone.get_current_timezone(),
    )

    if current_dt > deadline_dt:
        return {
            "passed": True,
            "deadline_time": deadline,
            "text": f"注文締切 {deadline.strftime('%H:%M')} は過ぎています。",
        }

    remaining = deadline_dt - current_dt
    minutes = int(remaining.total_seconds() // 60)
    hours, remain_minutes = divmod(minutes, 60)

    if hours > 0:
        text = (
            f"注文締切は {deadline.strftime('%H:%M')} です。"
            f" あと {hours}時間{remain_minutes}分です。"
        )
    else:
        text = f"注文締切は {deadline.strftime('%H:%M')} です。あと {remain_minutes}分です。"

    return {
        "passed": False,
        "deadline_time": deadline,
        "text": text,
    }


def get_department_or_404(company_code, department_code):
    try:
        return Department.objects.select_related("company").get(
            company__public_code=company_code,
            public_code=department_code,
            company__is_active=True,
            is_active=True,
        )
    except Department.DoesNotExist as exc:
        raise Http404("指定された企業または部署が見つかりません。") from exc


def get_order_form_context(company_code, department_code):
    department = get_department_or_404(company_code, department_code)
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    menus = list(Menu.objects.filter(is_active=True).order_by("display_order", "id"))
    today_order = (
        Order.objects.filter(
            department=department,
            order_date=today,
        )
        .prefetch_related(
            Prefetch(
                "items",
                queryset=OrderItem.objects.select_related("menu").order_by(
                    "menu__display_order", "menu__id"
                ),
            )
        )
        .first()
    )
    yesterday_order = (
        Order.objects.filter(
            department=department,
            order_date=yesterday,
        )
        .prefetch_related("items__menu")
        .first()
    )

    quantities = {}
    source_label = None

    if today_order:
        quantities = {item.menu_id: item.quantity for item in today_order.items.all()}
        source_label = "本日保存済みの注文"
    elif yesterday_order:
        quantities = {
            item.menu_id: item.quantity for item in yesterday_order.items.all()
        }
        source_label = "前日の注文"

    menu_rows = [
        {
            "menu": menu,
            "quantity": quantities.get(menu.id, 0),
        }
        for menu in menus
    ]

    return {
        "department": department,
        "company": department.company,
        "menu_rows": menu_rows,
        "deadline": get_deadline_status(today),
        "source_label": source_label,
        "today": today,
    }


def parse_quantities(post_data, menus):
    quantities = {}
    errors = []

    for menu in menus:
        raw_value = post_data.get(f"menu_{menu.id}", "0").strip() or "0"
        try:
            quantity = int(raw_value)
        except ValueError:
            errors.append(f"{menu.name} の数量は整数で入力してください。")
            continue

        if quantity < 0:
            errors.append(f"{menu.name} の数量は 0 以上で入力してください。")
            continue

        quantities[menu] = quantity

    return quantities, errors


@transaction.atomic
def submit_order(department, quantities, order_date=None):
    if order_date is None:
        order_date = timezone.localdate()

    deadline = get_deadline_status(order_date)
    if deadline["passed"]:
        raise ValueError("締切を過ぎているため、注文を更新できません。")

    order, _ = Order.objects.get_or_create(
        department=department,
        order_date=order_date,
        defaults={
            "company": department.company,
            "status": OrderStatus.SUBMITTED,
            "submitted_at": timezone.now(),
        },
    )

    order.company = department.company
    order.status = OrderStatus.SUBMITTED
    order.submitted_at = timezone.now()
    order.save()

    order.items.all().delete()

    items = [
        OrderItem(order=order, menu=menu, quantity=quantity)
        for menu, quantity in quantities.items()
        if quantity > 0
    ]
    if items:
        OrderItem.objects.bulk_create(items)

    return order


def get_dashboard_context(target_date=None):
    if target_date is None:
        target_date = timezone.localdate()

    all_departments = list(
        Department.objects.filter(company__is_active=True, is_active=True)
        .select_related("company")
        .order_by("company__name", "name", "id")
    )
    orders = list(
        Order.objects.filter(order_date=target_date)
        .select_related("company", "department")
        .prefetch_related("items__menu")
        .order_by("company__name", "department__name", "id")
    )

    menu_totals = list(
        OrderItem.objects.filter(order__order_date=target_date)
        .values("menu__name")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("menu__name")
    )
    company_totals = list(
        OrderItem.objects.filter(order__order_date=target_date)
        .values("order__company__name")
        .annotate(total_quantity=Sum("quantity"))
        .order_by("order__company__name")
    )

    total_count = sum(
        row["total_quantity"] for row in menu_totals if row["total_quantity"] is not None
    )

    deadline = get_deadline_status(target_date)
    ordered_department_ids = {order.department_id for order in orders}
    department_statuses = []
    for department in all_departments:
        if department.id in ordered_department_ids:
            status = "注文済み"
            status_class = "done"
        elif deadline["passed"]:
            status = "締切超過"
            status_class = "danger"
        else:
            status = "未注文"
            status_class = "waiting"

        department_statuses.append(
            {
                "company_name": department.company.name,
                "department_name": department.name,
                "status": status,
                "status_class": status_class,
            }
        )

    order_cards = [
        {
            "company_name": order.company.name,
            "department_name": order.department.name,
            "items": [
                {
                    "menu_name": item.menu.name,
                    "quantity": item.quantity,
                }
                for item in order.items.all()
            ],
        }
        for order in orders
    ]

    return {
        "target_date": target_date,
        "deadline": deadline,
        "total_count": total_count,
        "ordered_count": len(ordered_department_ids),
        "all_count": len(all_departments),
        "menu_totals": menu_totals,
        "company_totals": company_totals,
        "department_statuses": department_statuses,
        "order_cards": order_cards,
    }


def get_delivery_list_context(target_date=None):
    if target_date is None:
        target_date = timezone.localdate()

    orders = list(
        Order.objects.filter(order_date=target_date)
        .select_related("company", "department")
        .prefetch_related("items__menu")
        .order_by("company__name", "department__name", "id")
    )

    company_groups = []
    company_map = {}
    grand_total = 0

    for order in orders:
        items = []
        delivery_total = 0
        for item in order.items.all():
            subtotal = item.menu.price * item.quantity
            delivery_total += subtotal
            items.append(
                {
                    "menu_name": item.menu.name,
                    "price": item.menu.price,
                    "quantity": item.quantity,
                    "subtotal": subtotal,
                }
            )

        delivery_row = {
            "company_name": order.company.name,
            "department_name": order.department.name,
            "items": items,
            "delivery_total": delivery_total,
        }
        grand_total += delivery_total

        if order.company_id not in company_map:
            company_map[order.company_id] = {
                "company_name": order.company.name,
                "deliveries": [],
                "company_total": 0,
            }
            company_groups.append(company_map[order.company_id])

        company_map[order.company_id]["deliveries"].append(delivery_row)
        company_map[order.company_id]["company_total"] += delivery_total

    return {
        "target_date": target_date,
        "company_groups": company_groups,
        "grand_total": grand_total,
    }


def get_order_history_context(target_date=None, limit=100):
    orders = Order.objects.select_related("company", "department").prefetch_related(
        "items__menu"
    )
    if target_date:
        orders = orders.filter(order_date=target_date)

    orders = list(
        orders.order_by("-order_date", "company__name", "department__name", "id")[:limit]
    )

    history_rows = [
        {
            "order_date": order.order_date,
            "company_name": order.company.name,
            "department_name": order.department.name,
            "items": [
                {
                    "menu_name": item.menu.name,
                    "quantity": item.quantity,
                }
                for item in order.items.all()
            ],
        }
        for order in orders
    ]

    return {
        "history_rows": history_rows,
        "limit": limit,
        "target_date": target_date,
    }


def build_qr_data_uri(url):
    image = qrcode.make(url)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def get_company_directory_context(base_order_url):
    companies = (
        Company.objects.filter(is_active=True)
        .prefetch_related(
            Prefetch(
                "departments",
                queryset=Department.objects.filter(is_active=True).order_by("name", "id"),
            )
        )
        .order_by("name", "id")
    )

    company_rows = []
    for company in companies:
        departments = []
        for department in company.departments.all():
            order_url = f"{base_order_url}{company.public_code}/{department.public_code}/"
            departments.append(
                {
                    "name": department.name,
                    "public_code": department.public_code,
                    "order_url": order_url,
                }
            )

        company_rows.append(
            {
                "name": company.name,
                "public_code": company.public_code,
                "departments": departments,
            }
        )

    return {
        "company_rows": company_rows,
    }


def get_qr_directory_context(base_order_url):
    context = get_company_directory_context(base_order_url)

    for company in context["company_rows"]:
        for department in company["departments"]:
            department["qr_data_uri"] = build_qr_data_uri(department["order_url"])

    return context


def build_delivery_pdf(target_date=None):
    context = get_delivery_list_context(target_date=target_date)
    buffer = BytesIO()

    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
    styles = getSampleStyleSheet()
    styles["Title"].fontName = "HeiseiKakuGo-W5"
    styles["Heading2"].fontName = "HeiseiKakuGo-W5"
    styles["Normal"].fontName = "HeiseiKakuGo-W5"

    document = SimpleDocTemplate(buffer, pagesize=A4)
    story = [
        Paragraph("配送リスト", styles["Title"]),
        Spacer(1, 12),
        Paragraph(str(context["target_date"]), styles["Normal"]),
        Spacer(1, 16),
    ]

    if context["company_groups"]:
        for index, company_group in enumerate(context["company_groups"]):
            if index > 0:
                story.append(PageBreak())
            story.append(Paragraph(company_group["company_name"], styles["Title"]))
            story.append(Spacer(1, 12))
            for delivery in company_group["deliveries"]:
                story.append(Paragraph(delivery["department_name"], styles["Heading2"]))
                for item in delivery["items"]:
                    story.append(
                        Paragraph(
                            (
                                f'{item["menu_name"]}: '
                                f'{item["price"]}円 x {item["quantity"]}食 = {item["subtotal"]}円'
                            ),
                            styles["Normal"],
                        )
                    )
                story.append(
                    Paragraph(f'部署合計: {delivery["delivery_total"]}円', styles["Normal"])
                )
                story.append(Spacer(1, 10))
            story.append(
                Paragraph(f'企業合計: {company_group["company_total"]}円', styles["Normal"])
            )
            story.append(Spacer(1, 10))
    else:
        story.append(Paragraph("対象日の注文はありません。", styles["Normal"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph(f'全体合計: {context["grand_total"]}円', styles["Normal"]))

    document.build(story)
    buffer.seek(0)
    return buffer
