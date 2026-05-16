
# from rest_framework.renderers import BaseRenderer
# from weasyprint import HTML

# class PDFRenderer(BaseRenderer):
#     media_type = "application/pdf"
#     format = "pdf"

#     def render(self, data, media_type=None, renderer_context=None):
#         """
#         Converte os dados em PDF usando o WeasyPrint.
#         """
#         html_content = data.get("html_content", "")   
        
    
#         if isinstance(html_content, dict):
#             html_content = str(html_content)  

#         if html_content:
#             pdf = HTML(string=html_content).write_pdf()
#             return pdf
#         return b""