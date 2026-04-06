import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import operationApprovalApi from './api';
import { useAuth } from '../../hooks/useAuth';

const MOBILE_BREAKPOINT = 768;

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

export default function useDashboardPage() {
  const { user, can } = useAuth();
  const navigate = useNavigate();
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);
  const [loading, setLoading] = useState(true);
  const [statsError, setStatsError] = useState('');
  const [stats, setStats] = useState({
    in_approval_count: 0,
    executed_count: 0,
    rejected_count: 0,
    execution_failed_count: 0,
  });

  const capabilities = useMemo(
    () => ({
      canBrowse: can('ragflow_documents', 'view'),
      canViewDocumentHistory: can('kb_documents', 'view'),
      canUploadKb: can('kb_documents', 'upload'),
    }),
    [can]
  );

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadStats = async () => {
      setLoading(true);
      setStatsError('');
      try {
        const data = await operationApprovalApi.getStats();
        if (cancelled) return;
        setStats({
          in_approval_count: Number(data?.in_approval_count || 0),
          executed_count: Number(data?.executed_count || 0),
          rejected_count: Number(data?.rejected_count || 0),
          execution_failed_count: Number(data?.execution_failed_count || 0),
        });
      } catch (requestError) {
        if (cancelled) return;
        setStatsError(requestError?.message || '加载审批统计失败');
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    loadStats();
    return () => {
      cancelled = true;
    };
  }, []);

  const cards = useMemo(
    () => [
      {
        key: 'in_approval',
        title: '审批中',
        value: stats.in_approval_count,
        color: '#2563eb',
        onClick: () => navigate('/approvals?status=in_approval'),
      },
      {
        key: 'executed',
        title: '已执行',
        value: stats.executed_count,
        color: '#15803d',
        onClick: () => navigate('/approvals?status=executed'),
      },
      {
        key: 'rejected',
        title: '已驳回',
        value: stats.rejected_count,
        color: '#dc2626',
        onClick: () => navigate('/approvals?status=rejected'),
      },
      {
        key: 'execution_failed',
        title: '执行失败',
        value: stats.execution_failed_count,
        color: '#b91c1c',
        onClick: () => navigate('/approvals?status=execution_failed'),
      },
    ],
    [navigate, stats]
  );

  const quickActions = useMemo(() => {
    const actions = [
      {
        key: 'approvals',
        label: '查看审批',
        color: '#2563eb',
        onClick: () => navigate('/approvals'),
      },
    ];

    if (capabilities.canUploadKb) {
      actions.push({
        key: 'upload',
        label: '提交上传申请',
        color: '#059669',
        onClick: () => navigate('/upload'),
      });
    }
    if (capabilities.canViewDocumentHistory) {
      actions.push({
        key: 'document-history',
        label: '查看文档记录',
        color: '#7c3aed',
        onClick: () => navigate('/document-history'),
      });
    }
    if (capabilities.canBrowse) {
      actions.push({
        key: 'browser',
        label: '浏览文档',
        color: '#0f766e',
        onClick: () => navigate('/browser'),
      });
    }

    return actions;
  }, [capabilities.canBrowse, capabilities.canUploadKb, capabilities.canViewDocumentHistory, navigate]);

  return {
    user,
    isMobile,
    loading,
    statsError,
    cards,
    quickActions,
  };
}
