"""
Cross-Product Coordination API Endpoints

This module provides REST API endpoints for managing cross-product coordination
within the WCG ecosystem. Enables centralized coordination between FuzeAgent,
FuzeFront, HubHit, DeployAI, and other WCG products.
"""

from fastapi import APIRouter, HTTPException, Query, Path, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import logging
import asyncpg
from .database import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/coordination", tags=["Cross-Product Coordination"])


# Pydantic Models
class ProductRegistration(BaseModel):
    id: str = Field(..., description="Unique product identifier")
    name: str = Field(..., description="Product display name")
    version: str = Field(..., description="Current product version")
    endpoints: List[str] = Field(default=[], description="API endpoints exposed")
    dependencies: List[str] = Field(default=[], description="Product dependencies")
    resource_requirements: Dict[str, Any] = Field(
        default={}, description="Resource needs"
    )
    team_contacts: List[str] = Field(default=[], description="Team contact information")
    priority_level: int = Field(default=5, ge=1, le=10, description="Business priority")
    metadata: Dict[str, Any] = Field(default={}, description="Additional metadata")


class CoordinationRequestCreate(BaseModel):
    requesting_product: str = Field(..., description="Product making the request")
    target_products: List[str] = Field(
        ..., description="Target products for coordination"
    )
    coordination_type: str = Field(..., description="Type of coordination needed")
    scope: str = Field(default="product_group", description="Coordination scope")
    priority: str = Field(default="medium", description="Request priority")
    title: str = Field(..., description="Brief title for the request")
    description: str = Field(..., description="Detailed description")
    resource_requirements: Dict[str, Any] = Field(
        default={}, description="Required resources"
    )
    proposed_timeline: Dict[str, Any] = Field(
        default={}, description="Proposed timeline"
    )


class CoordinationResolution(BaseModel):
    resolution_plan: Dict[str, Any] = Field(..., description="Detailed resolution plan")
    resolver_id: str = Field(..., description="ID of the resolver")
    notes: Optional[str] = Field(None, description="Additional resolution notes")


class ResourceAllocationCreate(BaseModel):
    product_id: str = Field(..., description="Product requesting allocation")
    resource_type: str = Field(..., description="Type of resource")
    resource_name: str = Field(..., description="Specific resource name")
    allocation_details: Dict[str, Any] = Field(
        default={}, description="Allocation specifics"
    )
    valid_until: Optional[datetime] = Field(None, description="Allocation expiry")


# Product Registration Endpoints
@router.post(
    "/products/register", summary="Register a new product in coordination system"
)
async def register_product(product: ProductRegistration):
    """Register a new product in the cross-product coordination system"""
    try:
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO product_registry (
                    id, name, version, endpoints, dependencies,
                    resource_requirements, team_contacts, priority_level,
                    metadata, registered_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id) DO UPDATE SET
                    name = $2, version = $3, endpoints = $4, dependencies = $5,
                    resource_requirements = $6, team_contacts = $7,
                    priority_level = $8, metadata = $9, updated_at = $11
            """,
                product.id,
                product.name,
                product.version,
                product.endpoints,
                product.dependencies,
                product.resource_requirements,
                product.team_contacts,
                product.priority_level,
                product.metadata,
                datetime.utcnow(),
                datetime.utcnow(),
            )

        return {
            "status": "success",
            "product_id": product.id,
            "message": "Product registered successfully",
        }

    except Exception as e:
        logger.error(f"Error registering product {product.id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to register product: {str(e)}"
        )


@router.get("/products", summary="List all registered products")
async def list_products(
    priority_min: int = Query(1, ge=1, le=10, description="Minimum priority level"),
    active_only: bool = Query(True, description="Show only active products"),
):
    """List all products registered in the coordination system"""
    try:
        async with get_db_connection() as conn:
            products = await conn.fetch(
                """
                SELECT id, name, version, priority_level, metadata, 
                       endpoints, dependencies, registered_at, updated_at
                FROM product_registry 
                WHERE priority_level >= $1
                ORDER BY priority_level DESC, name ASC
            """,
                priority_min,
            )

        return {
            "products": [dict(product) for product in products],
            "total_count": len(products),
        }

    except Exception as e:
        logger.error(f"Error listing products: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list products: {str(e)}"
        )


@router.get("/products/{product_id}", summary="Get specific product details")
async def get_product(product_id: str = Path(..., description="Product ID")):
    """Get detailed information about a specific product"""
    try:
        async with get_db_connection() as conn:
            product = await conn.fetchrow(
                """
                SELECT * FROM product_registry WHERE id = $1
            """,
                product_id,
            )

        if not product:
            raise HTTPException(
                status_code=404, detail=f"Product {product_id} not found"
            )

        # Get active coordination requests involving this product
        async with get_db_connection() as conn:
            coordination_requests = await conn.fetch(
                """
                SELECT id, title, coordination_type, priority, status, created_at
                FROM coordination_requests 
                WHERE requesting_product = $1 
                   OR $1 = ANY(string_to_array(replace(replace(target_products::text, '[', ''), ']', ''), ','))
                ORDER BY created_at DESC LIMIT 10
            """,
                product_id,
            )

        return {
            "product": dict(product),
            "active_coordination_requests": [
                dict(req) for req in coordination_requests
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get product: {str(e)}")


# Coordination Request Endpoints
@router.post("/requests", summary="Create a new coordination request")
async def create_coordination_request(request: CoordinationRequestCreate):
    """Create a new cross-product coordination request"""
    try:
        # Validate requesting product exists
        async with get_db_connection() as conn:
            requesting_product = await conn.fetchrow(
                """
                SELECT id FROM product_registry WHERE id = $1
            """,
                request.requesting_product,
            )

        if not requesting_product:
            raise HTTPException(
                status_code=400,
                detail=f"Requesting product {request.requesting_product} not found",
            )

        # Create coordination request
        async with get_db_connection() as conn:
            request_id = await conn.fetchval(
                """
                INSERT INTO coordination_requests (
                    requesting_product, target_products, coordination_type,
                    scope, priority, title, description, resource_requirements,
                    proposed_timeline, stakeholders, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id
            """,
                request.requesting_product,
                request.target_products,
                request.coordination_type,
                request.scope,
                request.priority,
                request.title,
                request.description,
                request.resource_requirements,
                request.proposed_timeline,
                [],  # stakeholders - could be auto-populated
                datetime.utcnow(),
                datetime.utcnow(),
            )

        # Log coordination history
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO coordination_history (
                    coordination_request_id, action, actor_type, details
                ) VALUES ($1, $2, $3, $4)
            """,
                request_id,
                "created",
                "system",
                {"created_via": "api"},
            )

        return {
            "status": "success",
            "request_id": str(request_id),
            "message": "Coordination request created successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating coordination request: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to create coordination request: {str(e)}"
        )


@router.get("/requests", summary="List coordination requests")
async def list_coordination_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    product_id: Optional[str] = Query(None, description="Filter by product"),
    limit: int = Query(50, ge=1, le=200, description="Max number of results"),
):
    """List coordination requests with optional filters"""
    try:
        where_conditions = []
        params = []
        param_count = 0

        if status:
            param_count += 1
            where_conditions.append(f"status = ${param_count}")
            params.append(status)

        if priority:
            param_count += 1
            where_conditions.append(f"priority = ${param_count}")
            params.append(priority)

        if product_id:
            param_count += 1
            where_conditions.append(
                f"(requesting_product = ${param_count} OR ${param_count} = ANY(string_to_array(replace(replace(target_products::text, '[', ''), ']', ''), ',')))"
            )
            params.append(product_id)

        where_clause = (
            " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        )
        param_count += 1
        params.append(limit)

        query = f"""
            SELECT id, requesting_product, target_products, coordination_type,
                   scope, priority, status, title, description, created_at, updated_at
            FROM coordination_requests
            {where_clause}
            ORDER BY 
                CASE priority 
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2  
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                END,
                created_at DESC
            LIMIT ${param_count}
        """

        async with get_db_connection() as conn:
            requests = await conn.fetch(query, *params)

        return {
            "coordination_requests": [dict(req) for req in requests],
            "total_count": len(requests),
        }

    except Exception as e:
        logger.error(f"Error listing coordination requests: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list coordination requests: {str(e)}"
        )


@router.get("/requests/{request_id}", summary="Get coordination request details")
async def get_coordination_request(
    request_id: str = Path(..., description="Coordination request ID")
):
    """Get detailed information about a specific coordination request"""
    try:
        async with get_db_connection() as conn:
            request = await conn.fetchrow(
                """
                SELECT * FROM coordination_requests WHERE id = $1
            """,
                request_id,
            )

        if not request:
            raise HTTPException(
                status_code=404, detail=f"Coordination request {request_id} not found"
            )

        # Get coordination history
        async with get_db_connection() as conn:
            history = await conn.fetch(
                """
                SELECT action, actor_id, actor_type, details, timestamp
                FROM coordination_history 
                WHERE coordination_request_id = $1
                ORDER BY timestamp ASC
            """,
                request_id,
            )

        return {
            "coordination_request": dict(request),
            "history": [dict(h) for h in history],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting coordination request {request_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get coordination request: {str(e)}"
        )


@router.put("/requests/{request_id}/resolve", summary="Resolve coordination request")
async def resolve_coordination_request(
    request_id: str = Path(..., description="Coordination request ID"),
    resolution: CoordinationResolution = ...,
):
    """Resolve a coordination request with a specific plan"""
    try:
        async with get_db_connection() as conn:
            # Check if request exists and is pending
            existing_request = await conn.fetchrow(
                """
                SELECT id, status FROM coordination_requests WHERE id = $1
            """,
                request_id,
            )

        if not existing_request:
            raise HTTPException(
                status_code=404, detail=f"Coordination request {request_id} not found"
            )

        if existing_request["status"] not in ["pending", "in_progress"]:
            raise HTTPException(
                status_code=400,
                detail=f"Request is already {existing_request['status']}",
            )

        # Update request status and resolution
        async with get_db_connection() as conn:
            await conn.execute(
                """
                UPDATE coordination_requests SET
                    status = 'resolved',
                    resolution_plan = $2,
                    resolved_at = $3,
                    updated_at = $4
                WHERE id = $1
            """,
                request_id,
                resolution.resolution_plan,
                datetime.utcnow(),
                datetime.utcnow(),
            )

        # Log resolution in history
        async with get_db_connection() as conn:
            await conn.execute(
                """
                INSERT INTO coordination_history (
                    coordination_request_id, action, actor_id, actor_type, details
                ) VALUES ($1, $2, $3, $4, $5)
            """,
                request_id,
                "resolved",
                resolution.resolver_id,
                "agent",
                {
                    "resolution_plan": resolution.resolution_plan,
                    "notes": resolution.notes,
                },
            )

        return {
            "status": "success",
            "request_id": request_id,
            "message": "Coordination request resolved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resolving coordination request {request_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to resolve coordination request: {str(e)}"
        )


# Resource Management Endpoints
@router.post("/resources/allocate", summary="Allocate resources to a product")
async def allocate_resource(allocation: ResourceAllocationCreate):
    """Allocate a resource to a specific product"""
    try:
        async with get_db_connection() as conn:
            allocation_id = await conn.fetchval(
                """
                INSERT INTO resource_allocations (
                    product_id, resource_type, resource_name, allocation_details,
                    valid_until, status, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """,
                allocation.product_id,
                allocation.resource_type,
                allocation.resource_name,
                allocation.allocation_details,
                allocation.valid_until,
                "active",
                datetime.utcnow(),
                datetime.utcnow(),
            )

        return {
            "status": "success",
            "allocation_id": str(allocation_id),
            "message": "Resource allocated successfully",
        }

    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=409,
            detail=f"Resource {allocation.resource_name} of type {allocation.resource_type} is already allocated",
        )
    except Exception as e:
        logger.error(f"Error allocating resource: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to allocate resource: {str(e)}"
        )


@router.get("/resources", summary="List resource allocations")
async def list_resource_allocations(
    product_id: Optional[str] = Query(None, description="Filter by product"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    status: Optional[str] = Query(None, description="Filter by status"),
):
    """List current resource allocations"""
    try:
        where_conditions = []
        params = []
        param_count = 0

        if product_id:
            param_count += 1
            where_conditions.append(f"product_id = ${param_count}")
            params.append(product_id)

        if resource_type:
            param_count += 1
            where_conditions.append(f"resource_type = ${param_count}")
            params.append(resource_type)

        if status:
            param_count += 1
            where_conditions.append(f"status = ${param_count}")
            params.append(status)

        where_clause = (
            " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        )

        query = f"""
            SELECT ra.*, pr.name as product_name
            FROM resource_allocations ra
            LEFT JOIN product_registry pr ON ra.product_id = pr.id
            {where_clause}
            ORDER BY ra.created_at DESC
        """

        async with get_db_connection() as conn:
            allocations = await conn.fetch(query, *params)

        return {
            "resource_allocations": [dict(alloc) for alloc in allocations],
            "total_count": len(allocations),
        }

    except Exception as e:
        logger.error(f"Error listing resource allocations: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list resource allocations: {str(e)}"
        )


# Dashboard and Status Endpoints
@router.get("/status", summary="Get overall coordination system status")
async def get_coordination_status():
    """Get overall status of the cross-product coordination system"""
    try:
        async with get_db_connection() as conn:
            # Get request counts by status
            request_stats = await conn.fetch("""
                SELECT status, priority, COUNT(*) as count
                FROM coordination_requests 
                GROUP BY status, priority
                ORDER BY status, priority
            """)

            # Get product count
            product_count = await conn.fetchval("""
                SELECT COUNT(*) FROM product_registry
            """)

            # Get resource allocation stats
            resource_stats = await conn.fetch("""
                SELECT resource_type, status, COUNT(*) as count
                FROM resource_allocations
                GROUP BY resource_type, status
            """)

            # Get recent activity
            recent_activity = await conn.fetch("""
                SELECT ch.action, ch.timestamp, cr.title, cr.requesting_product
                FROM coordination_history ch
                JOIN coordination_requests cr ON ch.coordination_request_id = cr.id
                ORDER BY ch.timestamp DESC
                LIMIT 10
            """)

        return {
            "system_status": "operational",
            "registered_products": product_count,
            "coordination_request_stats": [dict(stat) for stat in request_stats],
            "resource_allocation_stats": [dict(stat) for stat in resource_stats],
            "recent_activity": [dict(activity) for activity in recent_activity],
            "last_updated": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Error getting coordination status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get coordination status: {str(e)}"
        )


@router.get("/protocols", summary="List coordination protocols")
async def list_coordination_protocols():
    """List available coordination protocols and procedures"""
    try:
        async with get_db_connection() as conn:
            protocols = await conn.fetch("""
                SELECT protocol_name, coordination_type, scope, procedure_steps,
                       required_approvals, sla_requirements, is_active, version
                FROM coordination_protocols
                WHERE is_active = true
                ORDER BY protocol_name ASC
            """)

        return {
            "coordination_protocols": [dict(protocol) for protocol in protocols],
            "total_count": len(protocols),
        }

    except Exception as e:
        logger.error(f"Error listing coordination protocols: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list coordination protocols: {str(e)}"
        )
