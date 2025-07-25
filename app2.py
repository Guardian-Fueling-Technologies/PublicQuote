import streamlit as st
import pandas as pd
import requests
from PIL import Image
import fitz
import io
import base64
import random
import time
from io import BytesIO
from reportlab.lib.pagesizes import letter
from servertest import getAllPrice
from servertest import getAllTicket
from servertest import getDesc
from servertest import getParentByTicket
from datetime import datetime
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.colors import red, black 
from reportlab.platypus import Paragraph
import numpy as np
import re
from reportlab.graphics.renderPM import PMCanvas
from decimal import Decimal
from reportlab.pdfbase.pdfmetrics import registerFont
from reportlab.pdfbase.ttfonts import TTFont
import json
registerFont(TTFont('Arial','arial.ttf'))
from twilio.rest import Client
import os
# ["+19046767222","+13213770708"]

# remove nte exceeding add ticketid df NTE

def notify_it_on_error(ip_address, user_input):
    try:
        # Get Twilio credentials from environment variables
        account_sid = os.environ.get("account_sid")
        auth_token = os.environ.get("auth_token")
        from_number = os.environ.get("twilio_from") 
        to_numbers = os.environ.get("twilio_to")

        client = Client(account_sid, auth_token)

        message_body = (
            f"⚠️ Ticket Number Input Failed.\n"
            f"IP: {ip_address}\n"
            f"Input: {user_input}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        to_numbers = json.loads(to_numbers)
        print(to_numbers)

        # Send SMS to each recipient
        for to_number in to_numbers:
            message = client.messages.create(
                body=message_body,
                from_=from_number,
                to=to_number
            )
            print(f"SMS sent to {to_number}")

    except Exception as sms_error:
        print(f"SMS failed to send: {sms_error}")

current_date = datetime.now()
formatted_date = current_date.strftime("%m/%d/%Y")
if "ticketN" not in st.session_state:
    st.session_state.ticketN = None
if "pricingDf" not in st.session_state:
    st.session_state.pricingDf = None
if "ticketDf" not in st.session_state:
    st.session_state.ticketDf = None
if "TRatesDf" not in st.session_state:
    st.session_state.TRatesDf = None
if "LRatesDf" not in st.session_state:
    st.session_state.LRatesDf = None
if "misc_ops_df" not in st.session_state:
    st.session_state.misc_ops_df = None
if "edit" not in st.session_state:
    st.session_state.edit = None
if "workDescription" not in st.session_state:
    st.session_state.workDescription = ""
if "NTE_Quote" not in st.session_state:
    st.session_state.NTE_Quote = ""
if "editable" not in st.session_state:
    st.session_state.editable = None
if "refresh_button" not in st.session_state:
    st.session_state.refresh_button = None
if "workDesDf" not in st.session_state:
    st.session_state.workDesDf = None
if 'selected_branches' not in st.session_state:
    st.session_state.selected_branches = []
# if "branch" not in st.session_state:
#     st.session_state.branch = getBranch()
# if "parentDf" not in st.session_state:
#     st.session_state.parentDf = getBranch()
if 'expand_collapse_state' not in st.session_state:
    st.session_state.expand_collapse_state = True
# if 'filtered_ticket' not in st.session_state:
#     st.session_state.filtered_ticket = [event for event in st.session_state.filtered_ticket if event['BranchShortName'] in st.session_state.selected_branches]

def techPage():
    if "labor_df" not in st.session_state:
        st.session_state.labor_df = pd.DataFrame()
        st.session_state.trip_charge_df = pd.DataFrame()
        st.session_state.parts_df = pd.DataFrame()
        st.session_state.miscellaneous_charges_df = pd.DataFrame()
        st.session_state.materials_and_rentals_df = pd.DataFrame()
        st.session_state.subcontractor_df = pd.DataFrame()

    # try:
    if 'ticketN' in st.session_state and st.session_state.ticketN:
        if st.session_state.ticketDf is None:
            # st.session_state.refresh_button = False
            try:
                if re.match(r'^\d{2}(0[1-9]|1[0-2])(0[1-9]|[12][0-9]|3[01])-\d{4}$', st.session_state.ticketN):
                    st.session_state.ticketDf, st.session_state.LRatesDf, st.session_state.TRatesDf, st.session_state.misc_ops_df = getAllPrice(st.session_state.ticketN)
                else:
                    st.error("Invalid ticket ID format - must be YYMMDD-NNNN")
                    return

            except ValueError as ve:
                st.error("Invalid characters in ticket ID")
                notify_it_on_error(f"Invalid characters in ticket ID: {st.session_state.ticketN}", st.session_state.ticketN)
                return
            except Exception as e:
                st.error("Failed to retrieve ticket data. Please try again later.")
                return
            try:
                workDes = getDesc(ticket=st.session_state.ticketN)
            except Exception as e:
                st.error("Unable to load work description at this time.")
                return
            if workDes is None or workDes.empty:
                st.session_state.workDescription = "Please input"
                st.session_state.workDesDf = pd.DataFrame({"TicketID":[st.session_state.ticketN], "Incurred":[st.session_state.workDescription], "Proposed":[st.session_state.workDescription]})
            else:
                st.session_state.workDesDf = workDes
            try:
                st.session_state.labor_df, st.session_state.trip_charge_df, st.session_state.parts_df, \
                st.session_state.miscellaneous_charges_df, st.session_state.materials_and_rentals_df, \
                st.session_state.subcontractor_df = getAllTicket(ticket=st.session_state.ticketN)
            except Exception as e:
                st.error("Unable to load detailed ticket charges.")
                return    
        if len(st.session_state.ticketDf)==0:
            st.error("Please enter a ticket number or check the ticket number again")
        else:
            try:
                parentDf = getParentByTicket(st.session_state.ticketN)
            except Exception:
                st.error("Unable to load approval info. Please contact support.")
                return
            if parentDf["NTE_QUOTE"].get(0) is not None and int(parentDf["NTE_QUOTE"].get(0)) == 1:
                st.session_state.NTE_Quote = "QUOTE"
            else:
                st.session_state.NTE_Quote = "NTE"
            if parentDf["Editable"].get(0) is not None and parentDf["Editable"].get(0) != "":
                st.session_state.editable = int(parentDf["Editable"])
            else:
                st.session_state.editable = 1
            if parentDf["Status"].get(0) is not None and (parentDf["Status"].get(0) == "Approved" or parentDf["Status"].get(0) == "Processed"):
                st.error("this ticket is now in GP")
                st.session_state.editable = 0

            if st.session_state.get("miscellaneous_charges_df", None) is None or st.session_state.miscellaneous_charges_df.empty:
                misc_charges_data = {
                    'Description': [None],
                    'QTY': [None],
                    'UNIT Price': [None],
                    'EXTENDED': [None]
                }
                st.session_state.miscellaneous_charges_df = pd.DataFrame(misc_charges_data)

            if st.session_state.get("materials_and_rentals_df", None) is None or st.session_state.materials_and_rentals_df.empty:
                materials_rentals_data = {
                    'Description': [None],
                    'QTY': [None],
                    'UNIT Price': [None],
                    'EXTENDED': [None]
                }
                st.session_state.materials_and_rentals_df = pd.DataFrame(materials_rentals_data)

            if st.session_state.get("subcontractor_df", None) is None or st.session_state.subcontractor_df.empty:
                subcontractor_data = {
                    'Description': [None],
                    'QTY': [None],
                    'UNIT Price': [None],
                    'EXTENDED': [None]
                }
                st.session_state.subcontractor_df = pd.DataFrame(subcontractor_data)
            
            categories = ['Labor', 'Trip Charge', 'Parts', 'Miscellaneous Charges', 'Materials and Rentals', 'Subcontractor']

            category_totals = {}
            for category in categories:
                # with st.expander(category, expanded=st.session_state.expand_collapse_state):
                    table_df = getattr(st.session_state, f"{category.lower().replace(' ', '_')}_df")
                    # st.table(table_df)
                    if not table_df.empty and 'EXTENDED' in table_df.columns:
                        category_total = table_df['EXTENDED'].sum()
                        category_totals[category] = category_total

            total_price = 0.0
            taxRate = float(st.session_state.ticketDf['Tax_Rate'])
            category_table_data = []
            for category in categories:
                table_df = getattr(st.session_state, f"{category.lower().replace(' ', '_')}_df")
                if not table_df.empty:
                    category_table_data.append([f"{category} Total", category_totals[category]])
                    total_price += category_totals[category]
                else:
                    category_table_data.append([f"{category} Total", 0])

            total_price_with_tax = total_price * (1 + taxRate / 100.0)

            # category_df = pd.DataFrame(category_table_data, columns=["Category", "Total"])
            # transposed_category_df = category_df.T

            # table_style = f"width: 100%; font-size: 18px;"
            # st.markdown(f'<style>{table_style}</style>', unsafe_allow_html=True)
            # st.table(transposed_category_df)

            printH = f"**Price (Pre-Tax):${total_price:.2f}**"
            printM = f"**Estimated Sales Tax:${total_price*taxRate/100:.2f}**"
            printT = f"**Total (including Est. tax):${total_price_with_tax:.2f}**"
            printK = f'**NTE:${st.session_state.ticketDf["NTE"][0]:.2f}**'

            col1, col2, col3, col4 = st.columns(4)
            col1.write(printH)
            col2.write(printM)
            col3.write(printT)
            col4.write(printK)
            
            input_pdf = PdfReader(open('input.pdf', 'rb'))
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            c.setFont("Arial", 9)
            c.drawString(25, 675.55, str(st.session_state.ticketDf['CUST_NAME'].values[0]))
            c.drawString(25, 665.55, str(st.session_state.ticketDf['CUST_ADDRESS1'].values[0]))
            c.drawString(25, 655.55, str(st.session_state.ticketDf['CUST_ADDRESS2'].values[0]) + " " + str(st.session_state.ticketDf['CUST_ADDRESS3'].values[0]) + " " +
                        str(st.session_state.ticketDf['CUST_CITY'].values[0]) + " " + str(st.session_state.ticketDf['CUST_Zip'].values[0]))
            print((st.session_state.ticketDf["NTE"][0] > 0.00))
            if st.session_state.ticketDf["NTE"][0] > 0.00 and total_price_with_tax > st.session_state.ticketDf["NTE"][0]:
                    # Define box dimensions and position (adjust as needed)
                box_width = 200
                box_height = 50
                box_x = (letter[0] - box_width) *3 / 4 # Center horizontally
                box_y = 720 # Adjust vertical position

                # Draw the rectangle (box)
                c.setStrokeColor(red) # Border color
                c.setFillColor(red)   # Fill color (optional, can be white or transparent)
                c.rect(box_x, box_y, box_width, box_height, stroke=1, fill=0) # stroke=1 for border, fill=0 for no fill

                # Draw the "NTE EXCEEDED" text
                text_content = "NTE EXCEEDED"
                text_font_size = 24 # Large font size
                c.setFont("Helvetica-Bold", text_font_size) # Use a bold font and large size
                c.setFillColor(red) # Text color

                # Calculate text position to center it in the box
                text_width = c.stringWidth(text_content, "Helvetica-Bold", text_font_size)
                text_x = box_x + (box_width - text_width) / 2
                text_y = box_y + (box_height - text_font_size) / 2 # Simple vertical centering

                c.drawString(text_x, text_y, text_content)
            c.setFont("Arial", 9)
            c.setStrokeColor(black) # Border color
            c.setFillColor(black) 
            c.drawString(50, 582, str(st.session_state.ticketDf['LOC_LOCATNNM'].values[0]))
            c.drawString(50, 572, st.session_state.ticketDf['LOC_Address'].values[0] + " " + st.session_state.ticketDf['CITY'].values[0] + " " + 
                st.session_state.ticketDf['STATE'].values[0]+ " " + st.session_state.ticketDf['ZIP'].values[0])
            c.drawString(70, 542, str(st.session_state.ticketDf['MailDispatch'].values[0]))
            c.drawString(310, 582, str(st.session_state.ticketN))
            c.drawString(310, 562, str(st.session_state.ticketDf['Purchase_Order'].values[0]))
            
            NTE_QTE = st.session_state.NTE_Quote
            if NTE_QTE is not None:
                NTE_QTE = "NTE/Quote# " + str(NTE_QTE)
            else:
                NTE_QTE = "NTE/Quote# None"
                
            c.setFont("Arial", 8)
            c.drawString(444, 580.55, str(NTE_QTE))
            c.setFont("Arial", 9)
            c.drawString(470, 551, str(formatted_date))
            c.setFont("Arial", 9)

            text_box_width = 560
            text_box_height = 100
            
            incurred_text = str(st.session_state.workDesDf["Incurred"].get(0))
            proposed_text = str(st.session_state.workDesDf["Proposed"].get(0))
            general_description = incurred_text + proposed_text

            # if len(general_description) > 4500:
            #     if len(incurred_text) > 2500:
            #         incurred_text = str(st.session_state.workDesDf["Incurred"].get(0))[:2500] + " ... max of 2500 chars"
            #     if len(proposed_text) > 2000:
            #         proposed_text = str(st.session_state.workDesDf["Proposed"].get(0))[:2000] + " ... max of 2000 chars"
            
            general_description = (
                incurred_text + ", " + proposed_text
            )
            
            styles = getSampleStyleSheet()
            paragraph_style = styles["Normal"]
            if general_description is not None:
                paragraph = Paragraph(general_description, paragraph_style)
            else:
                paragraph = Paragraph("Nothing has been entered", paragraph_style)
                
            paragraph.wrapOn(c, text_box_width, text_box_height)
            paragraph_height = paragraph.wrapOn(c, text_box_width, text_box_height)[1]
            paragraph.drawOn(c, 25, 485.55 - paragraph_height)

            block_x = 7
            block_width = 577
            block_height = paragraph_height+10
            block_y = 387.55 - (block_height-100)
            border_width = 1.5
            right_block_x = block_x + 10
            right_block_y = block_y
            right_block_width = block_width
            right_block_height = block_height
            c.rect(right_block_x, right_block_y, right_block_width, right_block_height, fill=0)
            c.rect(right_block_x + border_width, right_block_y + border_width, right_block_width - 2 * border_width, right_block_height - 2 * border_width, fill=0)  # Inner border
            c.setFont("Arial", 9)
            # after
            y = 386.55 - (block_height-60)
            margin_bottom = 20
            first_page = True
            new_page_needed = False

            for category in categories:
                if new_page_needed:
                    c.showPage()
                    first_page = False
                    new_page_needed = False
                    y = 750

                table_df = getattr(st.session_state, f"{category.lower().replace(' ', '_')}_df")
                row_height = 20
                category_column_width = block_width / 7

                if table_df.notna().any().any():
                    table_rows = table_df.to_records(index=False)
                    column_names = table_df.columns
                    row_height = 20
                    if(len(column_names)==4):
                        category_column_width = block_width / 6
                    else:
                        category_column_width = block_width / 7

                    if not first_page and y - (len(table_rows) + 4) * row_height < margin_bottom:
                        c.showPage()
                        first_page = False
                        y = 750

                    x = 17
                    col_width = category_column_width
                    for col_name in column_names:
                        if category != 'Labor':
                            if col_name == 'Description':
                                col_width = category_column_width * 3
                            elif col_name in ['QTY', 'UNIT Price', 'EXTENDED', 'Incurred/Proposed']:
                                col_width = category_column_width
                        c.rect(x, y, col_width, row_height)
                        c.setFont("Arial", 9)
                        c.drawString(x + 5, y + 5, str(col_name))
                        x += col_width
                    y -= row_height
                    for row in table_rows:
                        x = 17
                        count = 0
                        next_width = None
                        for col in row:
                            if count == 0:
                                col_width = category_column_width * 3
                            else:
                                col_width = next_width if next_width else category_column_width

                            if col in ['Incurred', 'Proposed', None]:
                                col_width = category_column_width
                                next_width = category_column_width * 3
                            else:
                                next_width = None
                            if col is not None and isinstance(col, str):
                                match = re.match(r'^[^:\d.]+.*', col)
                                if match:
                                    if y - row_height < margin_bottom:
                                        c.showPage()
                                        first_page = False
                                        y = 750
                                    first_string = match.group()
                                    if category == 'Labor' or category == 'Miscellaneous Charges' or category == 'Trip Charge':
                                        first_string = re.sub(r":.*", "", first_string)
                                    if category == 'Labor':
                                        col_width = category_column_width
                                    c.rect(x, y, col_width, row_height)
                                    c.setFont("Arial", 9)
                                    crop = 47
                                    if len(str(first_string)) < crop:
                                        c.drawString(x + 5, y + 5, str(first_string))
                                    else:
                                        c.drawString(x + 5, y + 5, str(first_string)[:crop])
                            else:
                                if category == 'Labor':
                                    col_width = category_column_width
                                c.rect(x, y, col_width, row_height)
                                c.setFont("Arial", 9)
                                c.drawString(x + 5, y + 5, str(col))
                            x += col_width
                            count+=1
                        y -= row_height
                        if new_page_needed:
                            c.showPage()
                            first_page = False
                            new_page_needed = False
                            y = 750                    

                    category_total = np.round(table_df['EXTENDED'].sum(), 2)
                    c.rect(17, y, block_width, row_height)
                    c.drawRightString(block_width + 12, y + 5, f"{category} Total: {category_total}")
                    y -= row_height

                    if y < margin_bottom:
                        c.showPage()
                        first_page = False
                        y = 750
                        
            total_price_with_tax = total_price * (1 + taxRate / 100.0)
            c.rect(17, y, block_width, row_height)
            c.drawRightString(block_width + 12, y + 5, f"Price (Pre-Tax): ${total_price:.2f}")
            y -= row_height
            c.rect(17, y, block_width, row_height)
            c.drawRightString(block_width + 12, y + 5, f"Estimated Sales Tax: {total_price*taxRate/100:.2f}")
            y -= row_height
            c.rect(17, y, block_width, row_height)
            c.drawRightString(block_width + 12, y + 5, f"Total (including tax): ${total_price_with_tax:.2f}")

            c.save()
            buffer.seek(0)
            output_pdf = PdfWriter()

            input_pdf = PdfReader('input.pdf')
            text_pdf = PdfReader(buffer)

            for i in range(len(input_pdf.pages)):
                page = input_pdf.pages[i]
                if i == 0:
                    page.merge_page(text_pdf.pages[0])
                output_pdf.add_page(page)

            for page in text_pdf.pages[1:]:
                output_pdf.add_page(page)

            merged_buffer = io.BytesIO()
            output_pdf.write(merged_buffer)

            merged_buffer.seek(0)

            pdf_content = merged_buffer.read()
            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')
            pdf_bytes = base64.b64decode(pdf_base64)  
            pdf_stream = io.BytesIO(pdf_bytes) 
            pdf_document = fitz.open(stream=pdf_stream, filetype="pdf")
            dpi = 600
            col1, col2 = st.columns([10,1])
            for page_number in range(len(pdf_document)):
                page = pdf_document.load_page(page_number)
                img = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
                pil_img = Image.frombytes("RGB", [img.width, img.height], img.samples)
                col1.image(pil_img, caption=f"Page {page_number + 1}", use_column_width="always")
            pdf_document.close()

            # pdf_display = f'<embed src="data:application/pdf;base64,{pdf_base64}" width="100%" height="700" type="application/pdf">' 
            # st.download_button("Download PDF", merged_buffer, file_name=f'{st.session_state.ticketN}-quote.pdf', mime='application/pdf')
            # st.markdown(pdf_display, unsafe_allow_html=True)
            # pdf_display = F'<iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="1000" type="application/pdf"></iframe>'            
            # st.markdown(pdf_display, unsafe_allow_html=True)
            # st.write(pdf_display, unsafe_allow_html=True)

def main():
    st.set_page_config("Public Quote", layout="wide")
    params = st.query_params.to_dict()
    if st.session_state.ticketN:
        techPage()
    else:
        if st.session_state.ticketN is None and params:
            st.session_state.ticketN = params["TicketID"]
            st.rerun()
        else:
            st.write("Please put your ticketID after .net =  /?TicketID=230524-0171")

if __name__ == "__main__":
    main()
