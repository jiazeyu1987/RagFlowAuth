import { useCallback, useMemo, useState } from 'react';
import { notificationApi } from '../api';
import { CHANNEL_TYPES } from './constants';
import { flattenRules, normalizeEnabledRuleChannelTypes } from './helpers';

export default function useNotificationRuleSettings() {
  const [rulesGroups, setRulesGroups] = useState([]);

  const ruleItems = useMemo(() => flattenRules(rulesGroups), [rulesGroups]);
  const eventLabelByType = useMemo(
    () => Object.fromEntries(ruleItems.map((item) => [item.event_type, item.event_label])),
    [ruleItems]
  );

  const hydrateRules = useCallback((items) => {
    setRulesGroups(items || []);
  }, []);

  const toggleRule = useCallback((eventType, channelType) => {
    setRulesGroups((prev) => prev.map((group) => ({
      ...group,
      items: (group.items || []).map((item) => {
        if (item.event_type !== eventType) return item;
        const exists = (item.enabled_channel_types || []).includes(channelType);
        const next = exists
          ? item.enabled_channel_types.filter((value) => value !== channelType)
          : [...(item.enabled_channel_types || []), channelType];
        return { ...item, enabled_channel_types: normalizeEnabledRuleChannelTypes(next) };
      }),
    })));
  }, []);

  const saveRules = useCallback(async () => {
    const nextRulesGroups = await notificationApi.upsertRules({
      items: flattenRules(rulesGroups).map((item) => ({
        event_type: item.event_type,
        enabled_channel_types: item.enabled_channel_types || [],
      })),
    });
    setRulesGroups(nextRulesGroups);
    return nextRulesGroups;
  }, [rulesGroups]);

  return {
    rulesGroups,
    ruleItems,
    eventLabelByType,
    hydrateRules,
    toggleRule,
    saveRules,
    channelTypes: CHANNEL_TYPES,
  };
}
