"""AI-powered endpoints for generating content."""
import os
import httpx
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

router = APIRouter()

# Category labels for prompt context
CATEGORY_LABELS = {
    "tech": "技术开发",
    "ai": "AI人工智能",
    "product": "产品设计",
    "marketing": "市场营销",
    "education": "教育培训",
    "entertainment": "娱乐休闲",
    "finance": "金融投资",
    "healthcare": "医疗健康",
    "gaming": "游戏电竞",
    "social": "社交聊天",
    "news": "新闻资讯",
    "other": "其他",
}


class GenerateDescriptionRequest(BaseModel):
    """Request body for generating group description."""
    name: str = Field(..., min_length=1, max_length=255, description="群组名称")
    category: str = Field(default="other", description="分类标识")


class GenerateDescriptionResponse(BaseModel):
    """Response with generated description."""
    description: str
    model: str


async def _call_llm(prompt: str, model: Optional[str] = None) -> tuple[str, str]:
    """
    Call LLM API to generate text.
    Supports multiple LLM providers:
    1. OpenAI (OPENAI_API_KEY)
    2. SiliconFlow (SILICONFLOW_API_KEY)
    3. DeepSeek (DEEPSEEK_API_KEY)
    """
    model_name = model or os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    
    # Try OpenAI
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        return await _call_openai(openai_key, prompt, model_name)
    
    # Try SiliconFlow
    silicon_key = os.getenv("SILICONFLOW_API_KEY")
    if silicon_key:
        return await _call_siliconflow(silicon_key, prompt, model_name)
    
    # Try DeepSeek
    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        return await _call_deepseek(deepseek_key, prompt)
    
    raise HTTPException(
        status_code=503,
        detail="No LLM API key configured. Set OPENAI_API_KEY, SILICONFLOW_API_KEY, or DEEPSEEK_API_KEY."
    )


async def _call_openai(api_key: str, prompt: str, model: str) -> tuple[str, str]:
    """Call OpenAI API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的群组描述生成助手。请根据群组名称和分类，生成一段简洁、有吸引力的中文描述（50-150字）。直接返回描述内容，不要加引号或其他格式。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 200,
            },
        )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"OpenAI API error: {response.text}")
        data = response.json()
        return data["choices"][0]["message"]["content"].strip(), f"openai/{model}"


async def _call_siliconflow(api_key: str, prompt: str, model: str) -> tuple[str, str]:
    """Call SiliconFlow API (compatible with OpenAI format)."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.siliconflow.cn/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的群组描述生成助手。请根据群组名称和分类，生成一段简洁、有吸引力的中文描述（50-150字）。直接返回描述内容，不要加引号或其他格式。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 200,
            },
        )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"SiliconFlow API error: {response.text}")
        data = response.json()
        return data["choices"][0]["message"]["content"].strip(), f"siliconflow/{model}"


async def _call_deepseek(api_key: str, prompt: str) -> tuple[str, str]:
    """Call DeepSeek API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://api.deepseek.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个专业的群组描述生成助手。请根据群组名称和分类，生成一段简洁、有吸引力的中文描述（50-150字）。直接返回描述内容，不要加引号或其他格式。"},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 200,
            },
        )
        if response.status_code != 200:
            raise HTTPException(status_code=502, detail=f"DeepSeek API error: {response.text}")
        data = response.json()
        return data["choices"][0]["message"]["content"].strip(), "deepseek/chat"


@router.post("/generate-description", response_model=GenerateDescriptionResponse)
async def generate_description(request: GenerateDescriptionRequest):
    """
    Generate a group description based on name and category.
    
    Uses AI to create an engaging, concise description (50-150 Chinese characters).
    Supports OpenAI, SiliconFlow, and DeepSeek APIs.
    
    Environment variables:
    - OPENAI_API_KEY: OpenAI API key
    - SILICONFLOW_API_KEY: SiliconFlow API key  
    - DEEPSEEK_API_KEY: DeepSeek API key
    - LLM_MODEL: Model to use (default: gpt-3.5-turbo)
    """
    category_label = CATEGORY_LABELS.get(request.category, "其他")
    
    prompt = f"群组名称：{request.name}\n分类：{category_label}"
    
    try:
        description, model_used = await _call_llm(prompt)
        return GenerateDescriptionResponse(description=description, model=model_used)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
