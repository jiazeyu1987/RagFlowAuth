import {
  mergeAssistantAnswer,
  readCompletionStreamFrame,
  rollbackAssistantDraft,
  shouldRefreshSessionMessages,
} from './useChatStreamSupport';

describe('useChatStreamSupport', () => {
  const normalizeForCompare = (value) => String(value || '').replace(/\s+/g, ' ').trim();
  const containsReasoningMarkers = (value) => String(value || '').includes('<think');

  it('prefers the longer incremental answer when the stream resends the full prefix', () => {
    const next = mergeAssistantAnswer({
      current: 'hello',
      incoming: 'hello world',
      normalizeForCompare,
      containsReasoningMarkers,
    });

    expect(next).toBe('hello world');
  });

  it('merges partial overlap when the stream sends a tail fragment', () => {
    const next = mergeAssistantAnswer({
      current: 'hello wor',
      incoming: 'world again',
      normalizeForCompare,
      containsReasoningMarkers,
    });

    expect(next).toBe('hello world again');
  });

  it('keeps the longer reasoning payload when think markers are present', () => {
    const next = mergeAssistantAnswer({
      current: '<think>draft</think>',
      incoming: '<think>draft with more detail</think>',
      normalizeForCompare,
      containsReasoningMarkers,
    });

    expect(next).toBe('<think>draft with more detail</think>');
  });

  it('parses the explicit stream frame contract', () => {
    expect(
      readCompletionStreamFrame({
        code: 0,
        data: {
          answer: 'done',
          sources: [{ doc_id: 'doc-1' }],
        },
      })
    ).toEqual({
      code: 0,
      answer: 'done',
      sources: [{ doc_id: 'doc-1' }],
      message: '',
    });
  });

  it('rolls back a dangling assistant placeholder without duplicating the user question', () => {
    expect(
      rollbackAssistantDraft(
        [
          { role: 'user', content: 'hello' },
          { role: 'assistant', content: '', sources: [] },
        ],
        'hello'
      )
    ).toEqual([{ role: 'user', content: 'hello' }]);
  });

  it('only refreshes from persisted session data when the stream produced no visible answer', () => {
    expect(
      shouldRefreshSessionMessages({
        assistantMessage: '  ',
        stripThinkTags: (value) => value,
        receivedAnswerEvent: false,
        consumedSseEvent: false,
      })
    ).toBe(true);

    expect(
      shouldRefreshSessionMessages({
        assistantMessage: '<think>hidden</think>',
        stripThinkTags: () => '',
        receivedAnswerEvent: true,
        consumedSseEvent: true,
      })
    ).toBe(false);
  });
});
