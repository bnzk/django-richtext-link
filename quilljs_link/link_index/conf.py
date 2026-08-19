from django.conf import settings


def get_index_protect():
    """
    When True, deleting an object that is a link target raises
    LinkedObjectProtectedError (advisory protection, signal based -
    the index is derived data, so this is not DB level PROTECT).
    """
    return getattr(settings, "QUILLJS_LINK_INDEX_PROTECT", False)
