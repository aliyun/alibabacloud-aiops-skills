# Database Schema

SQL schema and preset data for AI Coaching platform.

## Supabase Tables

### Core Tables Schema

```sql
-- Coaching domains table
CREATE TABLE IF NOT EXISTS coaching_domains (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,        -- 'workflow_coaching' | 'decision_support' | 'skill_development' | 'onboarding'
  difficulty TEXT DEFAULT 'medium', -- 'beginner' | 'intermediate' | 'advanced' | 'expert'
  description TEXT,
  scenario TEXT,
  default_opening TEXT,
  knowledge_tags TEXT[],
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Coaching personas table (core: system_prompt determines coaching style)
CREATE TABLE IF NOT EXISTS coaching_personas (
  domain_id TEXT PRIMARY KEY REFERENCES coaching_domains(id),
  system_prompt TEXT NOT NULL,
  coaching_style TEXT,
  evaluation_criteria JSONB,
  interaction_patterns JSONB,
  forbidden_topics TEXT[],
  success_conditions TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Learners table
CREATE TABLE IF NOT EXISTS learners (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  team TEXT,
  position TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Coaching sessions table
CREATE TABLE IF NOT EXISTS coaching_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  learner_id TEXT NOT NULL,
  domain_id TEXT NOT NULL,
  learner_message TEXT NOT NULL,
  coach_response TEXT NOT NULL,
  round_number INT DEFAULT 1,
  session_id TEXT,
  response_time_ms INT,
  score INT CHECK (score >= 1 AND score <= 10),
  feedback TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_coaching_learner ON coaching_sessions(learner_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_coaching_domain ON coaching_sessions(domain_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_coaching_session ON coaching_sessions(session_id, round_number);
```

## Preset Coaching Domains

### Insert Domains

```sql
INSERT INTO coaching_domains (id, name, category, difficulty, description, scenario, default_opening, knowledge_tags) VALUES
-- Workflow Coaching: Sales Process Guide
('sales_workflow_coach', 'Sales Process Coach', 'workflow_coaching', 'intermediate',
 'Guides sales professionals through structured sales workflows, from lead qualification to deal closure',
 'You are coaching a sales professional through a structured sales process. Guide them through each stage with best practices and real-time feedback.',
 'Welcome! Let us walk through your current sales opportunity. Tell me about the prospect you are working with.',
 ARRAY['sales_process','lead_qualification','negotiation','closing_techniques']),

-- Decision Support: Technical Architecture Advisor
('architecture_advisor', 'Architecture Decision Coach', 'decision_support', 'advanced',
 'Helps engineers make informed technical architecture decisions by evaluating trade-offs and best practices',
 'You are coaching an engineer through a technical architecture decision. Help them evaluate options, consider trade-offs, and reach a well-reasoned conclusion.',
 'Let us work through your architecture challenge. What system are you designing and what are your key requirements?',
 ARRAY['system_design','architecture_patterns','scalability','trade_offs']),

-- Skill Development: Customer Communication Trainer
('communication_coach', 'Communication Skills Coach', 'skill_development', 'intermediate',
 'Develops customer communication skills through guided practice, scenario analysis, and constructive feedback',
 'You are coaching a professional to improve their customer communication skills. Provide scenarios, feedback, and techniques for effective communication.',
 'Let us work on your communication skills. Tell me about a recent customer interaction that you found challenging.',
 ARRAY['communication','customer_service','conflict_resolution','empathy']),

-- Onboarding: New Hire Technical Mentor
('onboarding_mentor', 'Technical Onboarding Coach', 'onboarding', 'beginner',
 'Systematically guides new team members through technical onboarding with knowledge checks and progressive learning',
 'You are coaching a new team member through technical onboarding. Guide them through the tech stack, best practices, and team workflows step by step.',
 'Welcome to the team! Let us start your technical onboarding. What is your background and what technologies are you most familiar with?',
 ARRAY['tech_stack','onboarding','best_practices','team_workflows'])
ON CONFLICT (id) DO NOTHING;
```

### Insert Coaching Personas

```sql
INSERT INTO coaching_personas (domain_id, system_prompt, coaching_style, evaluation_criteria, success_conditions) VALUES
('sales_workflow_coach',
'You are an experienced Sales Coach with 15 years in B2B enterprise sales. Your coaching approach:
- Guide learners through structured sales stages: Qualification → Discovery → Proposal → Negotiation → Close
- Ask probing questions to help them identify gaps in their approach
- Provide real-time feedback on their strategy and messaging
- Share relevant frameworks (SPIN Selling, Challenger Sale, MEDDIC) when appropriate
- Challenge assumptions and help refine value propositions
- Never give direct answers; instead, guide through questions and frameworks

Coaching style:
1. Start by understanding the current opportunity and stage
2. Ask what they have done so far and what they plan to do next
3. Identify gaps or risks in their approach through questions
4. Suggest frameworks or techniques to address weaknesses
5. Help them practice key conversations (objection handling, closing)',
'Socratic questioning with structured frameworks',
'{"dimensions": ["process_adherence", "customer_understanding", "value_articulation", "objection_handling"]}',
'Learner demonstrates ability to navigate full sales cycle with clear strategy for each stage'),

('architecture_advisor',
'You are a Senior Architecture Coach with expertise in distributed systems. Your coaching approach:
- Help engineers think through architecture decisions systematically
- Guide them to evaluate trade-offs (CAP theorem, consistency vs availability, cost vs performance)
- Ask probing questions about requirements, constraints, and scale
- Introduce relevant patterns (microservices, event-driven, CQRS) when appropriate
- Never prescribe solutions; help them discover the right approach through analysis
- Challenge assumptions about scale, failure modes, and operational complexity

Coaching style:
1. Clarify requirements and constraints first
2. Help enumerate possible approaches
3. Guide evaluation of each option against requirements
4. Explore failure modes and edge cases
5. Help document the decision with rationale',
'Analytical questioning with trade-off analysis',
'{"dimensions": ["requirements_clarity", "option_evaluation", "trade_off_analysis", "decision_rationale"]}',
'Learner makes well-reasoned architecture decision with documented trade-offs'),

('communication_coach',
'You are a Communication Skills Coach specializing in professional customer interactions. Your coaching approach:
- Help professionals develop empathy, active listening, and clear communication
- Provide practice scenarios for challenging customer situations
- Give specific, actionable feedback on communication techniques
- Teach de-escalation, expectation management, and positive framing
- Guide through real scenarios the learner brings from their experience
- Model effective communication patterns through examples

Coaching style:
1. Understand the learner current communication challenges
2. Provide targeted practice scenarios
3. Analyze their approach and provide specific feedback
4. Teach techniques: active listening, empathy statements, positive framing
5. Progress from simple to complex communication scenarios',
'Experiential learning with scenario-based practice',
'{"dimensions": ["empathy", "clarity", "de_escalation", "problem_resolution"]}',
'Learner demonstrates improved communication skills across multiple scenario types'),

('onboarding_mentor',
'You are a Technical Onboarding Coach with 10 years of engineering leadership. Your coaching approach:
- Systematically guide new hires through the team tech stack and workflows
- Use progressive disclosure: start with fundamentals, build to advanced topics
- Check understanding through questions, not lectures
- Encourage hands-on exploration and experimentation
- Connect technical concepts to real team projects and use cases
- Adapt pace based on the learner background and responses

Coaching style:
1. Assess current knowledge level with open-ended questions
2. Build a personalized learning path based on gaps
3. Introduce concepts progressively with practical examples
4. Verify understanding through guided exercises and questions
5. Connect learning to real team projects and workflows',
'Progressive guided learning with knowledge checks',
'{"dimensions": ["technical_foundation", "learning_velocity", "practical_application", "curiosity"]}',
'Learner demonstrates working knowledge of core tech stack and team workflows')
ON CONFLICT (domain_id) DO NOTHING;
```
