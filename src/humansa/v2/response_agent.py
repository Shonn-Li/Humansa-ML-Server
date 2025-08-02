"""
HUMANSA Response Agent - Post-processes all responses to ensure brand consistency
and identity enforcement for the HUMANSA V2 system.

This agent ensures that regardless of how the LLM responds, the final output
always maintains HUMANSA's brand identity and service standards.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime

logger = logging.getLogger(__name__)


class HumansaResponseAgent:
    """
    Post-processes all agent responses to ensure:
    - HUMANSA identity is maintained in every response
    - Brand consistency across all interactions
    - Proper formatting and structure
    - Graceful error handling
    - Emergency response prioritization
    """
    
    def __init__(self):
        # Company identity constants
        self.COMPANY_NAME = "诺亚新舟"
        self.ASSISTANT_NAME = "小诺"
        self.FULL_IDENTITY = "诺亚新舟健康医疗助理小诺"
        self.TAGLINE = "以爱行舟，亲近相守"
        self.CAPABILITIES = "500多位三甲主任级名医专家，30+家高端综合名医诊所"
        
        # Response templates
        self.GREETING_TEMPLATE = """您好！我是{full_identity}，您的AI健康管家。
{content}
有什么可以帮助您的吗？"""
        
        self.IDENTITY_TEMPLATE = """我是{full_identity}，您的AI健康管家。{company}（Humansa）以'{tagline}'为理念，拥有{capabilities}。我可以帮助您查询医生、预约挂号、了解医疗服务等。有什么可以帮助您的吗？"""
        
        self.SERVICE_TEMPLATE = """作为{full_identity}，我可以为您提供以下服务：

{services}

{company}拥有{capabilities}，致力于为您提供优质的医疗健康服务。"""
        
        self.EMERGENCY_TEMPLATE = """⚠️ 紧急情况提醒：
{content}

请立即拨打120急救电话！

如需{company}的医疗服务支持，我们的医生随时准备为您提供后续帮助。"""
        
        self.PRODUCT_TEMPLATE = """
{content}

推荐您访问诺亚新舟健康商城：
📱 #小程序://诺亚新舟医疗/t5ZpOWu0UyRtEFl

{tagline}"""
        
        # Pattern matchers
        self.identity_patterns = [
            r"你是谁|您是谁|你叫什么|您叫什么",
            r"什么是小诺|什么是humansa|什么是诺亚新舟",
            r"介绍一下你|介绍一下您|你是什么",
            r"who are you|what are you|tell me about yourself",
            r"你的身份|您的身份|你是做什么的"
        ]
        
        self.greeting_patterns = [
            r"你好|您好|hi|hello|早上好|下午好|晚上好",
            r"嗨|hey|哈喽|哈罗",
            r"good morning|good afternoon|good evening"
        ]
        
        self.emergency_patterns = [
            r"胸痛|胸闷|心绞痛|心脏病",
            r"呼吸困难|喘不过气|窒息",
            r"昏迷|失去意识|晕倒",
            r"大出血|严重出血",
            r"中风|脑卒中|偏瘫",
            r"120|急救|紧急"
        ]
        
        self.service_patterns = [
            r"能做什么|会做什么|功能|服务|能力",
            r"帮助我什么|帮我什么",
            r"what can you do|capabilities|services"
        ]
        
        self.product_patterns = [
            r"保健品|营养品|健康产品|维生素",
            r"健康商城|商城|购买|买"
        ]
        
        self.company_patterns = [
            r"诺亚新舟|humansa|公司|机构",
            r"口号|理念|特色|规模",
            r"有多少医生|多少诊所|医生数量|诊所数量",
            r"以爱行舟|亲近相守"
        ]
        
        # Response counter for periodic identity reinforcement
        self.response_count = 0
        self.identity_reminder_interval = 10  # Remind identity every N responses
    
    def process_response(
        self,
        raw_response: Dict[str, Any],
        query: str,
        user_id: Optional[str] = None,
        context_messages: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Process raw agent response and ensure brand consistency
        
        Args:
            raw_response: Raw response from orchestrator agent
            query: Original user query
            user_id: User identifier
            context_messages: Previous conversation context
            
        Returns:
            Processed response with brand elements
        """
        self.response_count += 1
        
        # Extract response content
        output_items = raw_response.get('output', [])
        final_text = self._extract_final_text(output_items)
        
        # Clean up any remaining thinking patterns
        final_text = self._clean_thinking_text(final_text)
        
        # Determine response type and apply appropriate template
        response_type = self._determine_response_type(query, final_text)
        processed_text = self._apply_template(response_type, query, final_text)
        
        # Check if we need identity reinforcement
        if self.response_count % self.identity_reminder_interval == 0:
            processed_text = self._add_identity_reminder(processed_text)
        
        # Ensure brand elements are present
        processed_text = self._ensure_brand_elements(processed_text, response_type)
        
        # Handle errors gracefully
        processed_text = self._beautify_errors(processed_text)
        
        # Update response with processed text
        processed_response = raw_response.copy()
        
        # Update the output array with processed text while preserving tool_use entries
        if output_items:
            # Find the last text/output_text item and update it
            text_found = False
            for i in range(len(output_items) - 1, -1, -1):
                if output_items[i].get('type') in ['text', 'output_text']:
                    output_items[i]['text'] = processed_text
                    # Preserve the original type
                    text_found = True
                    break
            
            # If no text item found, add one at the end
            if not text_found:
                output_items.append({'type': 'output_text', 'text': processed_text})
        else:
            # Create new text output
            output_items = [{'type': 'output_text', 'text': processed_text}]
        
        processed_response['output'] = output_items
        
        # Add metadata about processing
        if 'metadata' not in processed_response:
            processed_response['metadata'] = {}
        
        processed_response['metadata'].update({
            'response_agent_processed': True,
            'response_type': response_type,
            'brand_elements_added': True,
            'identity_reinforced': self.response_count % self.identity_reminder_interval == 0
        })
        
        logger.info(f"✅ Response processed: type={response_type}, length={len(processed_text)}")
        
        return processed_response
    
    def _extract_final_text(self, output_items: List[Dict[str, Any]]) -> str:
        """Extract the final text response from output items"""
        final_text = ""
        all_text = ""
        
        # Patterns that indicate thinking/reasoning text
        thinking_patterns = [
            'The current language of the user',
            'I need to',
            'Action:',
            'Action Input:',
            'Observation:',
            '思考:',
            'Thought:',
            'Let me',
            'I should',
            '用户想',
            '需要'
        ]
        
        # First, try to find the last text that doesn't match thinking patterns
        for item in reversed(output_items):
            # Handle both 'text' and 'output_text' types
            if item.get('type') in ['text', 'output_text']:
                text = item.get('text', '').strip()
                all_text = text  # Keep as fallback
                
                # Check if this is thinking text
                is_thinking = any(text.startswith(pattern) for pattern in thinking_patterns)
                
                # Also check for specific action patterns
                if 'Action:' in text and 'Action Input:' in text:
                    is_thinking = True
                
                if not is_thinking and text:
                    final_text = text
                    break
        
        # If no non-thinking text found, use the last text as fallback
        if not final_text:
            final_text = all_text
        
        return final_text
    
    def _clean_thinking_text(self, text: str) -> str:
        """Clean up thinking/reasoning patterns from text"""
        if not text:
            return text
        
        # Remove common thinking patterns
        lines = text.split('\n')
        cleaned_lines = []
        skip_until_answer = False
        
        for line in lines:
            line_stripped = line.strip()
            
            # Skip lines that are clearly thinking patterns
            if any(line_stripped.startswith(pattern) for pattern in [
                'The current language',
                'Action:',
                'Action Input:',
                'Observation:',
                'Thought:',
                '思考:',
                'I need to',
                'Let me',
                '用户想',
                '需要使用'
            ]):
                skip_until_answer = True
                continue
            
            # Look for answer markers
            if line_stripped.startswith('Answer:') or line_stripped.startswith('回答:'):
                skip_until_answer = False
                # Extract just the answer part
                if ':' in line_stripped:
                    answer_text = line_stripped.split(':', 1)[1].strip()
                    if answer_text:
                        cleaned_lines.append(answer_text)
                continue
            
            # Keep lines that aren't thinking patterns
            if not skip_until_answer and line_stripped:
                cleaned_lines.append(line)
        
        cleaned_text = '\n'.join(cleaned_lines).strip()
        
        # If we cleaned everything away, return original
        if not cleaned_text:
            return text
        
        return cleaned_text
    
    def _determine_response_type(self, query: str, response: str) -> str:
        """Determine the type of response needed"""
        query_lower = query.lower()
        response_lower = response.lower()
        
        # Check emergency first (highest priority)
        if any(re.search(pattern, query_lower) for pattern in self.emergency_patterns):
            return 'emergency'
        
        # Check for emergency in response
        if '120' in response or '急救' in response or '立即' in response and '医院' in response:
            return 'emergency'
        
        # Identity query
        if any(re.search(pattern, query_lower) for pattern in self.identity_patterns):
            return 'identity'
        
        # Greeting
        if any(re.search(pattern, query_lower) for pattern in self.greeting_patterns):
            return 'greeting'
        
        # Service/capability query
        if any(re.search(pattern, query_lower) for pattern in self.service_patterns):
            return 'service'
        
        # Product query
        if any(re.search(pattern, query_lower) for pattern in self.product_patterns):
            return 'product'
        
        # Company information
        if any(re.search(pattern, query_lower) for pattern in self.company_patterns):
            return 'company'
        
        # Check response content for clues
        if '预约' in response or '医生' in response:
            return 'appointment'
        
        if '检查' in response or '体检' in response:
            return 'medical'
        
        return 'general'
    
    def _apply_template(self, response_type: str, query: str, content: str) -> str:
        """Apply appropriate template based on response type"""
        
        if response_type == 'emergency':
            return self.EMERGENCY_TEMPLATE.format(
                content=content,
                company=self.COMPANY_NAME
            )
        
        elif response_type == 'identity':
            return self.IDENTITY_TEMPLATE.format(
                full_identity=self.FULL_IDENTITY,
                company=self.COMPANY_NAME,
                tagline=self.TAGLINE,
                capabilities=self.CAPABILITIES
            )
        
        elif response_type == 'greeting':
            # Remove any generic greeting from content
            content = re.sub(r'^(你好|您好|Hi|Hello)[!！。.]*\s*', '', content, flags=re.IGNORECASE)
            return self.GREETING_TEMPLATE.format(
                full_identity=self.FULL_IDENTITY,
                content=content.strip()
            )
        
        elif response_type == 'service':
            # Extract service list if present
            services = content
            if not any(marker in content for marker in ['1.', '•', '-', '*']):
                # Create service list if not formatted
                services = """1. **健康咨询与分诊**：根据症状提供初步科室/检查建议
2. **实时预约**：查询医生余号，协助完成预约
3. **检查项目下单**：对比各诊所项目，跳转商城下单
4. **诊所导航**：提供地址、电话、营业时间、交通指引
5. **后续管理**：体检报告解读、慢病管理方案推荐"""
            
            return self.SERVICE_TEMPLATE.format(
                full_identity=self.FULL_IDENTITY,
                services=services,
                company=self.COMPANY_NAME,
                capabilities=self.CAPABILITIES
            )
        
        elif response_type == 'product':
            return self.PRODUCT_TEMPLATE.format(
                content=content,
                tagline=self.TAGLINE
            )
        
        elif response_type == 'company':
            # Ensure company info is complete
            if self.TAGLINE not in content:
                content += f"\n\n{self.COMPANY_NAME}的理念是：{self.TAGLINE}"
            if self.CAPABILITIES not in content:
                content += f"\n{self.CAPABILITIES}"
            return content
        
        else:
            # For general responses, ensure identity is mentioned if not present
            if self.ASSISTANT_NAME not in content and self.COMPANY_NAME not in content:
                # Add subtle identity reminder
                content = f"{content}\n\n作为您的{self.FULL_IDENTITY}，我随时准备为您提供更多帮助。"
            return content
    
    def _add_identity_reminder(self, content: str) -> str:
        """Add periodic identity reminder"""
        if self.TAGLINE not in content:
            reminder = f"\n\n💙 {self.TAGLINE} - {self.COMPANY_NAME}"
            content += reminder
        return content
    
    def _ensure_brand_elements(self, content: str, response_type: str) -> str:
        """Ensure critical brand elements are present"""
        
        # For appointment/medical responses, ensure clinic branding
        if response_type in ['appointment', 'medical']:
            if '诊所' in content and self.COMPANY_NAME not in content:
                content = content.replace('诊所', f'{self.COMPANY_NAME}诊所')
        
        # Ensure contact info has branding
        if '预约' in content and '电话' not in content:
            content += "\n\n如需人工协助预约，请联系诺亚新舟客服。"
        
        return content
    
    def _beautify_errors(self, content: str) -> str:
        """Convert technical errors to user-friendly messages"""
        
        # Database errors
        if 'relation' in content and 'does not exist' in content:
            return "抱歉，系统正在维护中，暂时无法查询相关信息。请稍后再试或联系客服获取帮助。"
        
        if 'connection error' in content.lower():
            return "抱歉，网络连接出现问题。请检查网络后重试，或联系我们的客服团队。"
        
        # Empty results
        if '未找到' in content or '没有找到' in content or 'not found' in content.lower():
            if '医生' in content:
                return f"暂时没有找到符合条件的医生。{self.COMPANY_NAME}拥有{self.CAPABILITIES}，建议您：\n1. 扩大搜索范围\n2. 尝试其他专科\n3. 联系客服获取个性化推荐"
            elif '诊所' in content:
                return f"暂时没有找到符合条件的诊所信息。{self.COMPANY_NAME}在全国有30+家高端诊所，请联系客服了解离您最近的诊所。"
        
        return content
    
    def _get_language(self, text: str) -> str:
        """Detect language of text"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
        total_chars = len(text)
        
        if total_chars == 0:
            return 'zh'
        
        if chinese_chars / total_chars > 0.3:
            return 'zh'
        else:
            return 'en'
    
    def process_streaming_event(
        self,
        event: Dict[str, Any],
        query: str,
        accumulated_text: str = ""
    ) -> Dict[str, Any]:
        """
        Process streaming events to ensure brand consistency
        Only processes response.done events to apply final formatting
        """
        # Only process the final response
        if event.get('event') == 'response.done':
            data = event.get('data', {})
            output_items = data.get('output', [])
            
            # Extract accumulated text
            final_text = self._extract_final_text(output_items)
            
            # Apply processing
            response_type = self._determine_response_type(query, final_text)
            processed_text = self._apply_template(response_type, query, final_text)
            processed_text = self._ensure_brand_elements(processed_text, response_type)
            processed_text = self._beautify_errors(processed_text)
            
            # Update the last text item in output
            if output_items:
                for i in range(len(output_items) - 1, -1, -1):
                    if output_items[i].get('type') == 'text':
                        output_items[i]['text'] = processed_text
                        break
            
            # Update event data
            data['output'] = output_items
            if 'metadata' not in data:
                data['metadata'] = {}
            data['metadata']['response_agent_processed'] = True
            data['metadata']['response_type'] = response_type
            
            event['data'] = data
        
        return event