import logging
import os

import resend

resend.api_key = os.getenv("RESEND_API_KEY", "")
logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
FROM_EMAIL = os.getenv("FROM_EMAIL", "BlockPR <noreply@blockpr.com>")


async def send_verification_email(email: str, company_name: str, token: str) -> None:
    """Send email verification link."""
    verify_url = f"{FRONTEND_URL}/verify-email?token={token}"
    logger.warning(f"[DEV] Verification token for {email}: {token}")
    logger.warning(f"[DEV] Verify URL: {verify_url}")
    if not resend.api_key:
        return
    try:
      resend.Emails.send({
        "from": FROM_EMAIL,
        "to": email,
        "subject": "Verificá tu cuenta en BlockPR",
        "html": f"""
        <!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
        <body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:40px 0;">
            <tr><td align="center">
              <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
                <!-- Header -->
                <tr>
                  <td style="background:#1a56db;padding:32px 40px;text-align:center;">
                    <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;letter-spacing:-0.5px;">BlockPR</h1>
                    <p style="margin:4px 0 0;color:#bfdbfe;font-size:13px;">Certificación blockchain</p>
                  </td>
                </tr>
                <!-- Body -->
                <tr>
                  <td style="padding:40px 40px 32px;">
                    <h2 style="margin:0 0 12px;color:#111827;font-size:20px;font-weight:600;">Verificá tu cuenta</h2>
                    <p style="margin:0 0 8px;color:#6b7280;font-size:15px;line-height:1.6;">Hola <strong style="color:#111827;">{company_name}</strong>,</p>
                    <p style="margin:0 0 28px;color:#6b7280;font-size:15px;line-height:1.6;">Gracias por registrarte en BlockPR. Para activar tu cuenta y empezar a emitir certificados, confirmá tu dirección de email.</p>
                    <table cellpadding="0" cellspacing="0" style="margin:0 auto 28px;">
                      <tr>
                        <td style="background:#1a56db;border-radius:8px;">
                          <a href="{verify_url}" style="display:inline-block;padding:14px 32px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;letter-spacing:0.2px;">Verificar email</a>
                        </td>
                      </tr>
                    </table>
                    <p style="margin:0;color:#9ca3af;font-size:13px;line-height:1.6;">Este enlace expira en <strong>24 horas</strong>. Si no creaste esta cuenta, podés ignorar este email.</p>
                  </td>
                </tr>
                <!-- Footer -->
                <tr>
                  <td style="background:#f9fafb;padding:20px 40px;border-top:1px solid #e5e7eb;text-align:center;">
                    <p style="margin:0;color:#9ca3af;font-size:12px;">© 2026 BlockPR · Todos los derechos reservados</p>
                  </td>
                </tr>
              </table>
            </td></tr>
          </table>
        </body>
        </html>
        """,
      })
    except Exception as exc:
        logger.error(f"[EMAIL] Failed to send verification email: {exc}")


async def send_password_reset_email(email: str, company_name: str, token: str) -> None:
    """Send password reset link."""
    reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
    logger.warning(f"[DEV] Password reset token for {email}: {token}")
    logger.warning(f"[DEV] Reset URL: {reset_url}")
    if not resend.api_key:
        return
    try:
      resend.Emails.send({
        "from": FROM_EMAIL,
        "to": email,
        "subject": "Restablecer contraseña - BlockPR",
        "html": f"""
        <!DOCTYPE html>
        <html lang="es">
        <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
        <body style="margin:0;padding:0;background:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;">
          <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;padding:40px 0;">
            <tr><td align="center">
              <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">
                <!-- Header -->
                <tr>
                  <td style="background:#1a56db;padding:32px 40px;text-align:center;">
                    <h1 style="margin:0;color:#ffffff;font-size:24px;font-weight:700;letter-spacing:-0.5px;">BlockPR</h1>
                    <p style="margin:4px 0 0;color:#bfdbfe;font-size:13px;">Certificación blockchain</p>
                  </td>
                </tr>
                <!-- Body -->
                <tr>
                  <td style="padding:40px 40px 32px;">
                    <h2 style="margin:0 0 12px;color:#111827;font-size:20px;font-weight:600;">Restablecer contraseña</h2>
                    <p style="margin:0 0 8px;color:#6b7280;font-size:15px;line-height:1.6;">Hola <strong style="color:#111827;">{company_name}</strong>,</p>
                    <p style="margin:0 0 28px;color:#6b7280;font-size:15px;line-height:1.6;">Recibimos una solicitud para restablecer la contraseña de tu cuenta. Hacé click en el botón para crear una nueva contraseña.</p>
                    <table cellpadding="0" cellspacing="0" style="margin:0 auto 28px;">
                      <tr>
                        <td style="background:#1a56db;border-radius:8px;">
                          <a href="{reset_url}" style="display:inline-block;padding:14px 32px;color:#ffffff;font-size:15px;font-weight:600;text-decoration:none;letter-spacing:0.2px;">Restablecer contraseña</a>
                        </td>
                      </tr>
                    </table>
                    <p style="margin:0;color:#9ca3af;font-size:13px;line-height:1.6;">Este enlace expira en <strong>1 hora</strong>. Si no solicitaste esto, podés ignorar este email — tu contraseña no será modificada.</p>
                  </td>
                </tr>
                <!-- Footer -->
                <tr>
                  <td style="background:#f9fafb;padding:20px 40px;border-top:1px solid #e5e7eb;text-align:center;">
                    <p style="margin:0;color:#9ca3af;font-size:12px;">© 2026 BlockPR · Todos los derechos reservados</p>
                  </td>
                </tr>
              </table>
            </td></tr>
          </table>
        </body>
        </html>
        """,
      })
    except Exception as exc:
        logger.error(f"[EMAIL] Failed to send reset email: {exc}")
