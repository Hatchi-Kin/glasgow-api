from fastapi import APIRouter


router = APIRouter(tags=["Health"])


@router.get("/")
def read_root():
    return {"message": "Hello from Glasgow GitOps!", "status": "running"}


@router.get("/health")
def health_check():
    return {"status": "healthy"}
