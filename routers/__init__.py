from .start import router as start_router
from .academic import router as academic_router
from .kitchen import router as kitchen_router
from .chat_companion import router as chat_companion_router
from .devops import router as devops_router
from .community import router as community_router
from .gamification import router as gamification_router
from .knowledge_base import router as knowledge_base_router

ALL_ROUTERS = [
    start_router, academic_router, kitchen_router, chat_companion_router,
    devops_router, community_router, gamification_router, knowledge_base_router
]