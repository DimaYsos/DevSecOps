import os
import uuid
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import Organization, User, APIToken
from apps.tickets.models import Ticket, Incident, Comment
from apps.assets.models import Asset
from apps.webhooks.models import WebhookConfig
from apps.audit.models import AuditEvent

class Command(BaseCommand):
    help = "seed_data"

    def handle(self, *args, **options):
        if Organization.objects.exists():
            return

        flag = os.environ.get("CTF_FLAG", "flag{default}")

        org_acme = Organization.objects.create(
            name="Acme Corporation", slug="acme", plan="enterprise",
            settings_json={"features": ["sso", "audit", "webhooks"], "max_users": 50, "internal_key": flag},
        )
        org_globex = Organization.objects.create(
            name="Globex Industries", slug="globex", plan="pro",
            settings_json={"features": ["webhooks"], "max_users": 20},
        )
        org_public = Organization.objects.create(
            name="Public Demo Organization", slug="public-demo", plan="free",
            settings_json={"features": ["basic"], "max_users": 10},
        )

        admin_user = User.objects.create_superuser(
            username="sysadmin", email="admin@vulnops.local",
            password="SysAdm1n!2024", role="sys_admin",
            organization=org_acme, first_name="System", last_name="Admin",
        )
        admin_user.preferences = {"theme": "dark", "api_secret": flag}
        admin_user.save(update_fields=["preferences"])

        acme_admin = User.objects.create_user(
            username="acme_admin", email="admin@acme.local",
            password="AcmeAdm1n!", role="org_admin",
            organization=org_acme, first_name="Alice", last_name="Admin",
        )
        globex_admin = User.objects.create_user(
            username="globex_admin", email="admin@globex.local",
            password="GlobexAdm1n!", role="org_admin",
            organization=org_globex, first_name="Bob", last_name="Manager",
        )

        agent1 = User.objects.create_user(
            username="agent_carol", email="carol@acme.local",
            password="Agent!123", role="agent",
            organization=org_acme, first_name="Carol", last_name="Support",
            department="IT Support",
        )
        agent2 = User.objects.create_user(
            username="agent_dave", email="dave@globex.local",
            password="Agent!123", role="agent",
            organization=org_globex, first_name="Dave", last_name="Tech",
            department="Engineering",
        )

        user1 = User.objects.create_user(
            username="user_eve", email="eve@acme.local",
            password="User!1234", role="user",
            organization=org_acme, first_name="Eve", last_name="Employee",
            department="Marketing",
        )
        user2 = User.objects.create_user(
            username="user_frank", email="frank@globex.local",
            password="User!1234", role="user",
            organization=org_globex, first_name="Frank", last_name="Staff",
            department="Sales",
        )

        public_user = User.objects.create_user(
            username="public_user",
            email="public@vulnops.local",
            password="PublicPass123",
            role="user",
            organization=org_public,
            first_name="Public",
            last_name="User",
            department="General",
            bio="",
        )

        public_token = APIToken.objects.create(
            user=public_user,
            name="Public API Access",
            token="pub_tk_" + "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
            is_active=True,
        )

        svc_account = User.objects.create_user(
            username="svc_integration", email="svc@vulnops.local",
            password="Svc!Int3gration", role="service_account",
            organization=org_acme, first_name="Service", last_name="Bot",
            is_internal=True,
        )

        svc_token = APIToken.objects.create(
            user=svc_account, name="Integration Token",
            token="svc_tk_" + "x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4",
            is_active=True,
        )

        admin_token = APIToken.objects.create(
            user=admin_user, name="Admin Token",
            token="adm_tk_" + "z1y2x3w4v5u6t7s8r9q0p1o2n3m4l5k6",
            is_active=True,
        )

        now = timezone.now()

        tickets_data = [
            {"title": "VPN connection drops intermittently", "description": "Users in Building A report VPN disconnects every 30 minutes. Affects approximately 50 users. Started after the network upgrade last Friday.", "status": "open", "priority": "high", "category": "network", "reporter": user1, "assignee": agent1, "org": org_acme},
            {"title": "Cannot access shared drive S:", "description": "Access denied error when trying to map network drive S:\\\\SharedDocs. Was working yesterday. Need access for quarterly report deadline.", "status": "in_progress", "priority": "medium", "category": "storage", "reporter": user1, "assignee": agent1, "org": org_acme},
            {"title": "New laptop setup request", "description": "New hire starting Monday needs laptop configured with standard image, Office 365, and department-specific software (Adobe Creative Suite).", "status": "open", "priority": "low", "category": "provisioning", "reporter": acme_admin, "assignee": agent1, "org": org_acme},
            {"title": "Email not syncing on mobile", "description": "Outlook app on iPhone 15 stopped syncing after password change. Have already removed and re-added the account.", "status": "waiting_customer", "priority": "medium", "category": "email", "reporter": user1, "org": org_acme},
            {"title": "Server room temperature alert", "description": "Environmental monitoring shows server room B2 at 28C, threshold is 25C. HVAC maintenance required urgently.", "status": "escalated", "priority": "critical", "category": "infrastructure", "reporter": agent1, "assignee": acme_admin, "org": org_acme, "is_internal": True, "internal_notes": "HVAC vendor contract #AC-2024-0891. Emergency contact: 555-0199."},
            {"title": "Software license renewal - AutoCAD", "description": "AutoCAD 2024 licenses expire end of month. 15 seats need renewal. Budget approved under PO-2024-3421.", "status": "open", "priority": "medium", "category": "licensing", "reporter": acme_admin, "org": org_acme},
            {"title": "Printer jam on floor 3", "description": "HP LaserJet on floor 3 has persistent paper jam. Tray 2 seems misaligned. Asset tag: PRN-0042.", "status": "resolved", "priority": "low", "category": "hardware", "reporter": user1, "assignee": agent1, "org": org_acme},
            {"title": "Database performance degradation", "description": "Production PostgreSQL showing slow queries (>5s) on the reporting module since the last deployment. Need DBA review.", "status": "in_progress", "priority": "critical", "category": "database", "reporter": agent1, "assignee": acme_admin, "org": org_acme, "is_internal": True},
        ]

        created_tickets = []
        for i, td in enumerate(tickets_data):
            t = Ticket.objects.create(
                organization=td["org"], title=td["title"], description=td["description"],
                status=td["status"], priority=td["priority"], category=td["category"],
                reporter=td["reporter"], assignee=td.get("assignee"),
                is_internal=td.get("is_internal", False),
                internal_notes=td.get("internal_notes", ""),
                created_at=now - timedelta(days=30 - i),
            )
            created_tickets.append(t)

        globex_tickets = [
            {"title": "CRM integration failing", "description": "Salesforce sync has been failing since Tuesday. Error: API rate limit exceeded. Need to investigate throttling configuration.", "status": "in_progress", "priority": "high", "reporter": user2, "assignee": agent2, "org": org_globex},
            {"title": "Office 365 migration - Phase 2", "description": "Migrating remaining 200 mailboxes from on-prem Exchange to O365. Phase 1 completed successfully.", "status": "open", "priority": "high", "reporter": globex_admin, "assignee": agent2, "org": org_globex},
            {"title": "Security camera offline - Warehouse", "description": "Camera #7 in the main warehouse went offline at 3 AM. May be network issue or hardware failure.", "status": "open", "priority": "medium", "reporter": user2, "org": org_globex},
        ]
        for i, td in enumerate(globex_tickets):
            Ticket.objects.create(
                organization=td["org"], title=td["title"], description=td["description"],
                status=td["status"], priority=td["priority"],
                reporter=td["reporter"], assignee=td.get("assignee"),
                created_at=now - timedelta(days=15 - i),
            )

        pub_ticket = Ticket.objects.create(
            organization=org_public, title="Test ticket from public account",
            description="This is a sample ticket created by the public demo account for testing purposes.",
            status="open", priority="low", reporter=public_user,
        )

        Comment.objects.create(
            ticket=created_tickets[0], author=agent1,
            content="I've checked the VPN concentrator logs. Seeing timeout errors from the new firmware. Rolling back to previous version.",
            content_html="<p>I've checked the VPN concentrator logs. Seeing timeout errors from the new firmware. Rolling back to previous version.</p>",
        )
        Comment.objects.create(
            ticket=created_tickets[0], author=user1,
            content="Thanks Carol. Some users are still experiencing issues after the rollback. Can you check again?",
            content_html="<p>Thanks Carol. Some users are still experiencing issues after the rollback. Can you check again?</p>",
        )
        Comment.objects.create(
            ticket=created_tickets[1], author=agent1,
            content="Permissions issue confirmed. The service account password expired. Resetting now.",
            content_html="<p>Permissions issue confirmed. The service account password expired. Resetting now.</p>",
        )
        Comment.objects.create(
            ticket=pub_ticket, author=public_user,
            content="Adding a comment to the public test ticket.",
            content_html="<p>Adding a comment to the public test ticket.</p>",
        )

        Incident.objects.create(
            organization=org_acme, title="Major network outage - Building A",
            description="Complete network loss in Building A affecting 200+ users. Switch failure in MDF confirmed.",
            severity="critical", status="mitigating",
            reporter=agent1, commander=acme_admin,
            affected_services=["email", "vpn", "file-shares", "voip"],
            detected_at=now - timedelta(hours=6),
        )
        Incident.objects.create(
            organization=org_globex, title="Email delivery delays",
            description="Outbound emails delayed by 2-4 hours. Mail queue backing up on relay server.",
            severity="medium", status="investigating",
            reporter=agent2, commander=globex_admin,
            affected_services=["email"],
            detected_at=now - timedelta(hours=2),
        )

        assets_data = [
            {"name": "Core Switch A1", "tag": "NET-0001", "type": "network", "sn": "CSW-2024-A1001", "mfg": "Cisco", "model": "Catalyst 9300", "loc": "Building A MDF", "dept": "IT", "org": org_acme, "cost": 12500},
            {"name": "Web Server Prod-1", "tag": "SRV-0001", "type": "server", "sn": "SRV-2023-W1001", "mfg": "Dell", "model": "PowerEdge R750", "loc": "DC Rack A-04", "dept": "Engineering", "org": org_acme, "cost": 8900},
            {"name": "Alice's Laptop", "tag": "LPT-0001", "type": "laptop", "sn": "LPT-2024-0001", "mfg": "Lenovo", "model": "ThinkPad X1 Carbon", "loc": "Floor 2", "dept": "Management", "org": org_acme, "cost": 1899},
            {"name": "Floor 3 Printer", "tag": "PRN-0042", "type": "printer", "sn": "PRN-2022-0042", "mfg": "HP", "model": "LaserJet Pro M428", "loc": "Floor 3", "dept": "Shared", "org": org_acme, "cost": 450},
            {"name": "Adobe Creative Suite", "tag": "SW-0010", "type": "software", "sn": "", "mfg": "Adobe", "model": "CC Enterprise", "loc": "Virtual", "dept": "Marketing", "org": org_acme, "cost": 7200},
            {"name": "Globex DB Server", "tag": "SRV-G001", "type": "server", "sn": "SRV-2023-G001", "mfg": "HP", "model": "ProLiant DL380", "loc": "Globex DC", "dept": "IT", "org": org_globex, "cost": 11200},
            {"name": "Warehouse Camera #7", "tag": "CAM-0007", "type": "other", "sn": "CAM-2023-0007", "mfg": "Hikvision", "model": "DS-2CD2185FWD", "loc": "Warehouse", "dept": "Security", "org": org_globex, "cost": 350},
            {"name": "Public Test Asset", "tag": "PUB-0001", "type": "laptop", "sn": "PUB-TEST-001", "mfg": "Dell", "model": "Latitude 5540", "loc": "Demo", "dept": "General", "org": org_public, "cost": 999},
        ]
        for ad in assets_data:
            Asset.objects.create(
                organization=ad["org"], name=ad["name"], asset_tag=ad["tag"],
                asset_type=ad["type"], serial_number=ad["sn"],
                manufacturer=ad["mfg"], model=ad["model"],
                location=ad["loc"], department=ad["dept"],
                purchase_cost=ad["cost"], status="active",
            )

        WebhookConfig.objects.create(
            organization=org_acme, name="Slack Notifications",
            url="http://mock-webhook-receiver:9002/webhook/slack",
            secret="whsec_acme_slack_2024",
            events=["ticket.created", "ticket.updated", "incident.created"],
            created_by=acme_admin, is_active=True,
        )
        WebhookConfig.objects.create(
            organization=org_globex, name="PagerDuty Integration",
            url="http://mock-webhook-receiver:9002/webhook/pagerduty",
            secret="whsec_globex_pd_2024",
            events=["incident.created", "ticket.escalated"],
            created_by=globex_admin, is_active=True,
        )

        AuditEvent.objects.create(
            user=admin_user, organization=org_acme, action="login",
            resource_type="session", description="System admin logged in",
            ip_address="10.0.0.1",
        )

        self.stdout.write(self.style.SUCCESS("Done."))
