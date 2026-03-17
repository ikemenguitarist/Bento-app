from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from companies.models import Company, Department
from core.models import OrderDeadlineSetting
from menus.models import Menu
from orders.models import Order, OrderItem, OrderStatus
from orders.services import get_delivery_list_context


class DepartmentOrderViewTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme")
        self.department = Department.objects.create(
            company=self.company,
            name="Sales",
        )
        self.menu_a = Menu.objects.create(name="幕の内弁当", price=800, display_order=1)
        self.menu_b = Menu.objects.create(name="唐揚げ弁当", price=700, display_order=2)
        OrderDeadlineSetting.objects.create(
            order_deadline_time=time(23, 59),
            applies_from=date(2026, 1, 1),
            is_active=True,
        )

    def test_get_order_page(self):
        response = self.client.get(
            reverse(
                "orders:department-order",
                kwargs={
                    "company_slug": self.company.slug,
                    "department_slug": self.department.slug,
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "注文フォーム")
        self.assertContains(response, "幕の内弁当")

    def test_submit_order_creates_order_and_items(self):
        response = self.client.post(
            reverse(
                "orders:department-order",
                kwargs={
                    "company_slug": self.company.slug,
                    "department_slug": self.department.slug,
                },
            ),
            data={
                f"menu_{self.menu_a.id}": "2",
                f"menu_{self.menu_b.id}": "1",
            },
        )

        self.assertRedirects(
            response,
            reverse(
                "orders:thanks",
                kwargs={
                    "company_slug": self.company.slug,
                    "department_slug": self.department.slug,
                },
            ),
        )
        order = Order.objects.get(department=self.department)
        self.assertEqual(order.company, self.company)
        self.assertEqual(order.status, OrderStatus.SUBMITTED)
        self.assertEqual(order.items.count(), 2)
        self.assertTrue(
            OrderItem.objects.filter(order=order, menu=self.menu_a, quantity=2).exists()
        )

    def test_submit_replaces_existing_items(self):
        order = Order.objects.create(
            company=self.company,
            department=self.department,
            order_date=date.today(),
            status=OrderStatus.SUBMITTED,
        )
        OrderItem.objects.create(order=order, menu=self.menu_a, quantity=5)

        self.client.post(
            reverse(
                "orders:department-order",
                kwargs={
                    "company_slug": self.company.slug,
                    "department_slug": self.department.slug,
                },
            ),
            data={
                f"menu_{self.menu_a.id}": "0",
                f"menu_{self.menu_b.id}": "3",
            },
        )

        order.refresh_from_db()
        self.assertEqual(order.items.count(), 1)
        self.assertTrue(
            OrderItem.objects.filter(order=order, menu=self.menu_b, quantity=3).exists()
        )

    def test_submit_after_deadline_is_blocked(self):
        OrderDeadlineSetting.objects.all().delete()
        OrderDeadlineSetting.objects.create(
            order_deadline_time=time(0, 0),
            applies_from=date(2026, 1, 1),
            is_active=True,
        )

        response = self.client.post(
            reverse(
                "orders:department-order",
                kwargs={
                    "company_slug": self.company.slug,
                    "department_slug": self.department.slug,
                },
            ),
            data={f"menu_{self.menu_a.id}": "1"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Order.objects.exists())


class OrderAdminPagesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operator",
            password="test-pass-123",
        )
        self.client.force_login(self.user)
        self.company = Company.objects.create(name="Beta")
        self.company_two = Company.objects.create(name="Gamma")
        self.department_a = Department.objects.create(company=self.company, name="General")
        self.department_b = Department.objects.create(company=self.company, name="Tech")
        self.department_c = Department.objects.create(
            company=self.company_two,
            name="Support",
        )
        self.menu_a = Menu.objects.create(name="鮭弁当", price=850, display_order=1)
        self.menu_b = Menu.objects.create(name="生姜焼き弁当", price=900, display_order=2)
        OrderDeadlineSetting.objects.create(
            order_deadline_time=time(23, 59),
            applies_from=date(2026, 1, 1),
            is_active=True,
        )

        today = date.today()
        yesterday = today - timedelta(days=1)

        order_today = Order.objects.create(
            company=self.company,
            department=self.department_a,
            order_date=today,
            status=OrderStatus.SUBMITTED,
        )
        OrderItem.objects.create(order=order_today, menu=self.menu_a, quantity=2)
        OrderItem.objects.create(order=order_today, menu=self.menu_b, quantity=1)

        order_yesterday = Order.objects.create(
            company=self.company,
            department=self.department_b,
            order_date=yesterday,
            status=OrderStatus.SUBMITTED,
        )
        OrderItem.objects.create(order=order_yesterday, menu=self.menu_b, quantity=4)

        order_other_company = Order.objects.create(
            company=self.company_two,
            department=self.department_c,
            order_date=today,
            status=OrderStatus.SUBMITTED,
        )
        OrderItem.objects.create(order=order_other_company, menu=self.menu_b, quantity=2)

    def test_dashboard_page(self):
        response = self.client.get(reverse("orders:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "当日ダッシュボード")
        self.assertContains(response, "Beta")
        self.assertContains(response, "General")
        self.assertContains(response, "未注文")

    def test_dashboard_page_with_date_filter(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        response = self.client.get(reverse("orders:dashboard"), {"date": yesterday})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tech")
        self.assertContains(response, "生姜焼き弁当")
        self.assertNotContains(response, "鮭弁当")

    def test_delivery_list_page(self):
        response = self.client.get(reverse("orders:delivery-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "配送リスト")
        self.assertContains(response, "鮭弁当")
        self.assertContains(response, "850円")
        self.assertContains(response, "1700円")
        self.assertContains(response, "Beta")
        self.assertContains(response, "Gamma")
        self.assertContains(response, "企業合計: 2600円")
        self.assertContains(response, "企業合計: 1800円")
        self.assertContains(response, "全体合計: 4400円")

    def test_delivery_context_includes_prices_and_totals(self):
        context = get_delivery_list_context(target_date=date.today())

        self.assertEqual(context["grand_total"], 4400)
        self.assertEqual(len(context["company_groups"]), 2)
        self.assertEqual(context["company_groups"][0]["company_name"], "Beta")
        self.assertEqual(context["company_groups"][0]["company_total"], 2600)
        self.assertEqual(context["company_groups"][1]["company_name"], "Gamma")
        self.assertEqual(context["company_groups"][1]["company_total"], 1800)
        self.assertEqual(
            context["company_groups"][0]["deliveries"][0]["items"][0]["price"],
            850,
        )
        self.assertEqual(
            context["company_groups"][0]["deliveries"][0]["items"][0]["subtotal"],
            1700,
        )

    def test_delivery_pdf_page(self):
        response = self.client.get(reverse("orders:delivery-pdf"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_history_page(self):
        response = self.client.get(reverse("orders:history"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "注文履歴")
        self.assertContains(response, "生姜焼き弁当")

    def test_history_page_with_date_filter(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        response = self.client.get(reverse("orders:history"), {"date": yesterday})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tech")
        self.assertNotContains(response, "General</td>")

    def test_company_directory_page(self):
        response = self.client.get(reverse("orders:company-directory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "企業・部署一覧")
        self.assertContains(response, "Beta")
        self.assertContains(response, "General")
        self.assertContains(
            response,
            f"/orders/{self.company.slug}/{self.department_a.slug}/",
        )

    def test_qr_directory_page(self):
        response = self.client.get(reverse("orders:qr-directory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "QR 一覧")
        self.assertContains(response, "data:image/png;base64,")

    def test_operations_hub_page(self):
        response = self.client.get(reverse("orders:operations-hub"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "運営ハブ")
        self.assertContains(response, "企業管理")
        self.assertContains(response, "配送リストPDF")

    def test_root_path_redirects_to_operations_hub(self):
        response = self.client.get("/")

        self.assertRedirects(response, reverse("orders:operations-hub"))


class InternalPagesAuthTests(TestCase):
    def test_operations_hub_requires_login(self):
        response = self.client.get(reverse("orders:operations-hub"))

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("orders:operations-hub")}',
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("orders:dashboard"))

        self.assertRedirects(
            response,
            f'{reverse("login")}?next={reverse("orders:dashboard")}',
        )

    def test_public_order_page_is_accessible_without_login(self):
        company = Company.objects.create(name="Public")
        department = Department.objects.create(company=company, name="Sales")
        Menu.objects.create(name="幕の内弁当", price=800, display_order=1)
        OrderDeadlineSetting.objects.create(
            order_deadline_time=time(23, 59),
            applies_from=date(2026, 1, 1),
            is_active=True,
        )

        response = self.client.get(
            reverse(
                "orders:department-order",
                kwargs={
                    "company_slug": company.slug,
                    "department_slug": department.slug,
                },
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "注文フォーム")
