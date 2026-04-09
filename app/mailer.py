import smtplib
import sqlite3

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import DB_PATH, RECEIVER_EMAIL, SENDER_EMAIL, SENDER_PASSWORD


class ReportMailer:
    def __init__(
        self,
        db_path: str = DB_PATH,
        sender_email: str = SENDER_EMAIL,
        sender_password: str = SENDER_PASSWORD,
        receiver_email: str = RECEIVER_EMAIL,
    ) -> None:
        self.db_path = db_path
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.receiver_email = receiver_email

    def send_movie_report(self) -> None:
        """
        Generates a high-fidelity, dashboard-style HTML movie report
        with rock-solid UI alignment for email clients.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM movies")
                rows = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
        except Exception as e:
            print(f"Database Error: {e}")
            return

        def make_score_pill(label, score_val):
            """Creates a stable, rounded badge using nested tables."""
            if not score_val or score_val == "NDF" or score_val == "N/A":
                bg, text, border = "#f1f5f9", "#94a3b8", "#e2e8f0"
            else:
                try:
                    score = int(str(score_val).replace("%", ""))
                    if score >= 60:
                        bg, text, border = "#f0fdf4", "#16a34a", "#bbf7d0"
                    else:
                        bg, text, border = "#fef2f2", "#dc2626", "#fecaca"
                except ValueError:
                    bg, text, border = "#f1f5f9", "#94a3b8", "#e2e8f0"

            return f"""
            <table cellpadding="0" cellspacing="0" border="0" style="margin: 4px auto;">
                <tr>
                    <td style="background-color: {bg}; border: 1px solid {border}; border-radius: 12px; padding: 4px 10px; line-height: 1;">
                        <span style="color: {text}; font-size: 11px; font-weight: bold; font-family: sans-serif; white-space: nowrap;">
                            {label} {score_val}
                        </span>
                    </td>
                </tr>
            </table>"""

        body_rows = ""
        for row in rows:
            data = dict(zip(columns, row))

            raw_rating = str(data.get("rating") or "N/A")
            rating_parts = raw_rating.split("(", 1)
            main_rating = rating_parts[0].strip()
            sub_rating = f"({rating_parts[1]}" if len(rating_parts) > 1 else ""

            toma_pill = make_score_pill("🍅", data.get("tomatometer"))
            aud_pill = make_score_pill("🎟️", data.get("audience_score"))

            storyline = data.get("storyline", "")
            storyline = storyline[:160] + "..." if storyline and len(storyline) > 160 else storyline

            body_rows += f"""
            <tr style="border-bottom: 1px solid #f1f5f9;">
                <td style="padding: 20px 15px; vertical-align: top; width: 220px;">
                    <div style="font-weight: 700; color: #1e293b; font-size: 15px; margin-bottom: 2px;">{data.get('title')}</div>
                    <div style="color: #94a3b8; font-size: 12px;">Year: {data.get('year')}</div>
                </td>

                <td style="padding: 20px 10px; vertical-align: middle; text-align: center; width: 140px;">
                    <table cellpadding="0" cellspacing="0" border="0" style="margin: 0 auto;">
                        <tr>
                            <td style="border: 1.5px solid #475569; border-radius: 4px; padding: 3px 6px;">
                                <span style="color: #475569; font-size: 11px; font-weight: 800; font-family: sans-serif;">{main_rating}</span>
                            </td>
                        </tr>
                    </table>
                    <div style="color: #94a3b8; font-size: 10px; margin-top: 6px; line-height: 1.2; font-style: italic;">{sub_rating}</div>
                </td>

                <td style="padding: 20px 10px; vertical-align: middle; text-align: center; width: 120px;">
                    <div style="color: #475569; font-size: 12px; font-weight: 600; font-family: sans-serif;">{data.get('release_date') or '---'}</div>
                </td>

                <td style="padding: 10px; vertical-align: middle; text-align: center; width: 120px;">
                    {toma_pill}
                    {aud_pill}
                </td>

                <td style="padding: 20px 15px; color: #64748b; font-size: 13px; line-height: 1.5; vertical-align: top;">
                    {storyline}
                </td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="margin:0; padding:0; background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="padding: 40px 10px;">
                <tr>
                    <td align="center">
                        <table width="100%" border="0" cellspacing="0" cellpadding="0" style="max-width: 1000px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #e2e8f0;">

                            <tr>
                                <td style="background-color: #0f172a; padding: 35px 40px; text-align: left;">
                                    <h1 style="margin: 0; color: #ffffff; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">
                                        <span style="color: #ef4444;">RT</span> MOVIE INTELLIGENCE
                                    </h1>
                                    <p style="margin: 8px 0 0; color: #94a3b8; font-size: 13px; letter-spacing: 0.5px;">
                                        {len(rows)} TITLES PROCESSED &nbsp; | &nbsp; DATABASE SYNC COMPLETE
                                    </p>
                                </td>
                            </tr>

                            <tr>
                                <td style="padding: 0;">
                                    <table width="100%" border="0" cellspacing="0" cellpadding="0" style="border-collapse: collapse;">
                                        <thead>
                                            <tr style="background-color: #f8fafc; border-bottom: 2px solid #f1f5f9;">
                                                <th style="text-align: left; padding: 16px; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Movie Title</th>
                                                <th style="text-align: center; padding: 16px; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Rating</th>
                                                <th style="text-align: center; padding: 16px; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Release</th>
                                                <th style="text-align: center; padding: 16px; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Scores</th>
                                                <th style="text-align: left; padding: 16px; color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Storyline</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {body_rows}
                                        </tbody>
                                    </table>
                                </td>
                            </tr>

                            <tr>
                                <td style="padding: 30px; background-color: #f8fafc; text-align: center; border-top: 1px solid #f1f5f9;">
                                    <p style="margin: 0; color: #cbd5e1; font-size: 11px; letter-spacing: 1px;">
                                        AUTOMATED REPORT • GENERATED BY RT-SCRAPER-BOT
                                        <br>
                                        This report scans for 'Movie' only, TV Series are not included in final report.
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"🎬 RT Report: {len(rows)} Movies Synchronized"
        msg["From"] = self.sender_email
        msg["To"] = self.receiver_email
        msg.attach(MIMEText(html, "html"))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, self.receiver_email, msg.as_string())
            print(f"✨ Success! The premium report has been sent to {self.receiver_email}")
        except Exception as e:
            print(f"❌ SMTP Error: {e}")
