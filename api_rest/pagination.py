from rest_framework.pagination import PageNumberPagination

class StandardResultsSetPagination(PageNumberPagination):
    """
    Classe de paginação padrão para os endpoints que retornam listas de resultados.
    
    A configuração padrão define:
    - `page_size`: Número de itens por página (30).
    - `page_size_query_param`: Parâmetro de query para especificar o número de itens por página.
    - `max_page_size`: Número máximo de itens que podem ser solicitados por página (100).
    """
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 100