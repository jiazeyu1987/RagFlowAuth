import { policyKnowledgeApiMethods } from './policy/policyKnowledgeApi';
import { policyRagflowApiMethods } from './policy/policyRagflowApi';
import { policyAgentApiMethods } from './policy/policyAgentApi';
import { policyNasApiMethods } from './policy/policyNasApi';
import { policyPackageDrawingApiMethods } from './policy/policyPackageDrawingApi';

export const policyApiMethods = {
  ...policyKnowledgeApiMethods,
  ...policyRagflowApiMethods,
  ...policyAgentApiMethods,
  ...policyNasApiMethods,
  ...policyPackageDrawingApiMethods,
};
