import { policyKnowledgeApiMethods } from './policy/policyKnowledgeApi';
import { policyRagflowApiMethods } from './policy/policyRagflowApi';
import { policyAgentApiMethods } from './policy/policyAgentApi';
import { policyNasApiMethods } from './policy/policyNasApi';

export const policyApiMethods = {
  ...policyKnowledgeApiMethods,
  ...policyRagflowApiMethods,
  ...policyAgentApiMethods,
  ...policyNasApiMethods,
};
