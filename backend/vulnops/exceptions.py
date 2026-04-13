import traceback
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def verbose_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        response.data["detail_type"] = type(exc).__name__
        response.data["view"] = str(context.get("view", ""))
        response.data["request_path"] = str(context.get("request", {}).path if hasattr(context.get("request", {}), "path") else "")
        return response

    tb = traceback.format_exc()
    return Response(
        {
            "error": str(exc),
            "type": type(exc).__name__,
            "traceback": tb,
            "view": str(context.get("view", "")),
            "args": [str(a) for a in exc.args],
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
