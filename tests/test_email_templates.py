import unittest

from app.services.email_templates import render_action_email, render_otp_email
from app.services.email_verification_service import _build_email_message_content


class EmailTemplateTest(unittest.TestCase):
    def test_action_email_can_render_google_like_logo_layout_without_expiry_line(self) -> None:
        rendered = render_action_email(
            app_name="QuizzVN",
            recipient_name="Thanh",
            recipient_email="thanh@example.com",
            subject="Preview",
            title="Mời xác thực tài khoản quản trị",
            intro_lines=[
                "Bạn được mời gửi yêu cầu tài khoản quản trị.",
                "Bấm nút bên dưới để điền thông tin và xác thực OTP.",
            ],
            button_label="Mở form xác thực",
            button_url="http://localhost:8000/admin/invitations/accept?token=preview",
            brand_logo_url="http://localhost:8000/assets/email-logo.png",
        )

        self.assertIn('background:#ffffff', rendered.html_body)
        self.assertIn('background:#ffffff;border:1px solid #dadce0;border-radius:8px', rendered.html_body)
        self.assertIn('width="150"', rendered.html_body)
        self.assertIn('src="http://localhost:8000/assets/email-logo.png"', rendered.html_body)
        self.assertIn("thanh@example.com", rendered.html_body)
        self.assertIn("height:1px;background:#dadce0", rendered.html_body)
        self.assertNotIn("Liên kết này có hiệu lực", rendered.html_body)
        self.assertNotIn("10080", rendered.html_body)
        self.assertNotIn("Liên kết này có hiệu lực", rendered.text_body)


    def test_otp_email_uses_smaller_digit_type(self) -> None:
        rendered = render_otp_email(
            app_name="QuizzVN",
            recipient_name="Thanh",
            recipient_email="thanh@example.com",
            subject="OTP",
            title="OTP",
            intro="Use this OTP.",
            otp_code="095215",
            expires_minutes=20,
            brand_logo_url="http://localhost:8000/assets/email-logo.png",
        )

        self.assertIn("font-size:32px", rendered.html_body)
        self.assertNotIn("font-size:38px", rendered.html_body)

    def test_sent_html_email_keeps_logo_as_external_image(self) -> None:
        rendered = render_otp_email(
            app_name="QuizzVN",
            recipient_name="Thanh",
            recipient_email="thanh@example.com",
            subject="OTP",
            title="OTP",
            intro="Use this OTP.",
            otp_code="095215",
            expires_minutes=20,
            brand_logo_url="http://localhost:8000/assets/email-logo.png",
        )

        message = _build_email_message_content(
            "thanh@example.com",
            rendered.subject,
            rendered.text_body,
            rendered.html_body,
        )
        html_parts = [part for part in message.walk() if part.get_content_type() == "text/html"]
        image_parts = [part for part in message.walk() if part.get_content_maintype() == "image"]

        self.assertEqual(1, len(html_parts))
        self.assertIn('src="http://localhost:8000/assets/email-logo.png"', html_parts[0].get_content())
        self.assertEqual([], image_parts)


if __name__ == "__main__":
    unittest.main()
