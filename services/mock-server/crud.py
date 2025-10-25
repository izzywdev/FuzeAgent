"""
CRUD operations for FuzeAgent Mock Server
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from typing import List, Optional, Dict, Any, Type, TypeVar, Generic
from uuid import UUID
import math

import models, schemas

ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: UUID) -> Optional[ModelType]:
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None,
        search_fields: Optional[List[str]] = None
    ) -> tuple[List[ModelType], int]:
        query = db.query(self.model)
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    if isinstance(value, list):
                        query = query.filter(getattr(self.model, field).in_(value))
                    elif isinstance(value, str) and "%" in value:
                        query = query.filter(getattr(self.model, field).like(value))
                    else:
                        query = query.filter(getattr(self.model, field) == value)
        
        # Apply search
        if search and search_fields:
            search_conditions = []
            for field in search_fields:
                if hasattr(self.model, field):
                    search_conditions.append(
                        getattr(self.model, field).ilike(f"%{search}%")
                    )
            if search_conditions:
                query = query.filter(or_(*search_conditions))
        
        # Get total count before pagination
        total = query.count()
        
        # Apply sorting
        if sort_by and hasattr(self.model, sort_by):
            sort_column = getattr(self.model, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(asc(sort_column))
        
        # Apply pagination
        items = query.offset(skip).limit(limit).all()
        
        return items, total

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        obj_in_data = obj_in.model_dump() if hasattr(obj_in, 'model_dump') else obj_in.dict()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self, 
        db: Session, 
        *, 
        db_obj: ModelType, 
        obj_in: UpdateSchemaType
    ) -> ModelType:
        obj_data = obj_in.model_dump(exclude_unset=True) if hasattr(obj_in, 'model_dump') else obj_in.dict(exclude_unset=True)
        for field, value in obj_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: UUID) -> Optional[ModelType]:
        obj = db.query(self.model).get(id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def exists(self, db: Session, *, id: UUID) -> bool:
        return db.query(self.model).filter(self.model.id == id).first() is not None

# Organization CRUD
class CRUDOrganization(CRUDBase[models.Organization, schemas.OrganizationCreate, schemas.OrganizationUpdate]):
    def get_by_name(self, db: Session, *, name: str) -> Optional[models.Organization]:
        return db.query(self.model).filter(self.model.name == name).first()
    
    def create(self, db: Session, *, obj_in: schemas.OrganizationCreate) -> models.Organization:
        # First create the entity record
        entity = models.Entity(kind="organization")
        db.add(entity)
        db.flush()  # Flush to get the entity ID
        
        # Create the organization with the same ID as the entity
        obj_in_data = obj_in.model_dump()
        obj_in_data["id"] = entity.id
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_multi_with_teams(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> tuple[List[models.Organization], int]:
        search_fields = ["name", "description"]
        return self.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters,
            search=search,
            search_fields=search_fields
        )

organization = CRUDOrganization(models.Organization)

# Team CRUD
class CRUDTeam(CRUDBase[models.Team, schemas.TeamCreate, schemas.TeamUpdate]):
    def get_by_organization(
        self, 
        db: Session, 
        *, 
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.Team], int]:
        query = db.query(self.model).filter(self.model.organization_id == organization_id)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_multi_with_agents(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> tuple[List[models.Team], int]:
        search_fields = ["name", "description", "team_type"]
        return self.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters,
            search=search,
            search_fields=search_fields
        )

team = CRUDTeam(models.Team)

# Agent Template CRUD
class CRUDAgentTemplate(CRUDBase[models.AgentTemplate, schemas.AgentTemplateCreate, schemas.AgentTemplateUpdate]):
    def get_by_category(
        self, 
        db: Session, 
        *, 
        category: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.AgentTemplate], int]:
        query = db.query(self.model).filter(self.model.category == category)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_multi_with_search(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> tuple[List[models.AgentTemplate], int]:
        search_fields = ["template_name", "description", "model", "category"]
        return self.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters,
            search=search,
            search_fields=search_fields
        )

agent_template = CRUDAgentTemplate(models.AgentTemplate)

# Agent CRUD
class CRUDAgent(CRUDBase[models.Agent, schemas.AgentCreate, schemas.AgentUpdate]):
    def get_by_team(
        self, 
        db: Session, 
        *, 
        team_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.Agent], int]:
        query = db.query(self.model).filter(self.model.team_id == team_id)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_by_status(
        self, 
        db: Session, 
        *, 
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.Agent], int]:
        query = db.query(self.model).filter(self.model.status == status)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_multi_with_search(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> tuple[List[models.Agent], int]:
        search_fields = ["name", "role", "type", "model"]
        return self.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters,
            search=search,
            search_fields=search_fields
        )

agent = CRUDAgent(models.Agent)

# Goal CRUD
class CRUDGoal(CRUDBase[models.Goal, schemas.GoalCreate, schemas.GoalUpdate]):
    def get_by_organization(
        self, 
        db: Session, 
        *, 
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.Goal], int]:
        query = db.query(self.model).filter(self.model.organization_id == organization_id)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_by_status(
        self, 
        db: Session, 
        *, 
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.Goal], int]:
        query = db.query(self.model).filter(self.model.status == status)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_multi_with_search(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> tuple[List[models.Goal], int]:
        search_fields = ["title", "description"]
        return self.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters,
            search=search,
            search_fields=search_fields
        )

goal = CRUDGoal(models.Goal)

# Milestone CRUD
class CRUDMilestone(CRUDBase[models.Milestone, schemas.MilestoneCreate, schemas.MilestoneUpdate]):
    def get_by_goal(
        self, 
        db: Session, 
        *, 
        goal_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.Milestone], int]:
        query = db.query(self.model).filter(self.model.goal_id == goal_id)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_multi_with_search(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> tuple[List[models.Milestone], int]:
        search_fields = ["title"]
        return self.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters,
            search=search,
            search_fields=search_fields
        )

milestone = CRUDMilestone(models.Milestone)

# Task CRUD
class CRUDTask(CRUDBase[models.Task, schemas.TaskCreate, schemas.TaskUpdate]):
    def get_by_team(
        self, 
        db: Session, 
        *, 
        team_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.Task], int]:
        query = db.query(self.model).filter(self.model.team_id == team_id)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_by_agent(
        self, 
        db: Session, 
        *, 
        agent_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.Task], int]:
        query = db.query(self.model).filter(self.model.agent_id == agent_id)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_by_status(
        self, 
        db: Session, 
        *, 
        status: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.Task], int]:
        query = db.query(self.model).filter(self.model.status == status)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_multi_with_search(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> tuple[List[models.Task], int]:
        search_fields = ["title", "description", "progress_notes"]
        return self.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters,
            search=search,
            search_fields=search_fields
        )

task = CRUDTask(models.Task)

# Knowledge CRUD
class CRUDKnowledge(CRUDBase[models.Knowledge, schemas.KnowledgeCreate, schemas.KnowledgeUpdate]):
    def get_by_owner(
        self, 
        db: Session, 
        *, 
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.Knowledge], int]:
        query = db.query(self.model).filter(self.model.owner_id == owner_id)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_by_type(
        self, 
        db: Session, 
        *, 
        type: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.Knowledge], int]:
        query = db.query(self.model).filter(self.model.type == type)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_multi_with_search(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> tuple[List[models.Knowledge], int]:
        search_fields = ["title", "content_preview", "extracted_text"]
        return self.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters,
            search=search,
            search_fields=search_fields
        )

knowledge = CRUDKnowledge(models.Knowledge)

# Conversation CRUD
class CRUDConversation(CRUDBase[models.Conversation, schemas.ConversationCreate, schemas.ConversationUpdate]):
    def get_by_owner(
        self, 
        db: Session, 
        *, 
        owner_id: UUID
    ) -> Optional[models.Conversation]:
        return db.query(self.model).filter(self.model.owner_id == owner_id).first()

    def get_multi_with_search(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> tuple[List[models.Conversation], int]:
        search_fields = ["title"]
        return self.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters,
            search=search,
            search_fields=search_fields
        )

conversation = CRUDConversation(models.Conversation)

# Message CRUD
class CRUDMessage(CRUDBase[models.ConversationMessage, schemas.MessageCreate, schemas.MessageUpdate]):
    def get_by_conversation(
        self, 
        db: Session, 
        *, 
        conversation_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[models.ConversationMessage], int]:
        query = db.query(self.model).filter(self.model.conversation_id == conversation_id)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_multi_with_search(
        self, 
        db: Session, 
        skip: int = 0, 
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc",
        filters: Optional[Dict[str, Any]] = None,
        search: Optional[str] = None
    ) -> tuple[List[models.ConversationMessage], int]:
        search_fields = ["content"]
        return self.get_multi(
            db=db,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=filters,
            search=search,
            search_fields=search_fields
        )

message = CRUDMessage(models.ConversationMessage)

# Utility functions
def paginate_results(items: List[Any], total: int, page: int, size: int) -> schemas.PaginatedResponse:
    """Create a paginated response from items and total count"""
    pages = math.ceil(total / size) if total > 0 else 0
    return schemas.PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages
    )
