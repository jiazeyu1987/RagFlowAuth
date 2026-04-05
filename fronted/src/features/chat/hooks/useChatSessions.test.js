import React from 'react';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import { chatApi } from '../api';
import { useChatSessions } from './useChatSessions';

jest.mock('../api', () => ({
  chatApi: {
    listMyChats: jest.fn(),
    listChatSessions: jest.fn(),
    createChatSession: jest.fn(),
    deleteChatSessions: jest.fn(),
    renameChatSession: jest.fn(),
  },
}));

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

function HookHarness() {
  const hook = useChatSessions({
    restoreSourcesIntoMessages: (chatId, sessionId, messages) => messages,
  });

  return (
    <div>
      <div data-testid="selected-chat">{hook.selectedChatId || ''}</div>
      <div data-testid="selected-session">{hook.selectedSessionId || ''}</div>
      <div data-testid="session-count">{hook.sessions.length}</div>
      <button type="button" data-testid="select-chat-b" onClick={() => hook.actions.setSelectedChatId('chat-b')}>
        select-chat-b
      </button>
    </div>
  );
}

describe('useChatSessions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('ignores stale session responses after switching chats', async () => {
    const user = userEvent.setup();
    const firstChatSessions = deferred();
    const secondChatSessions = deferred();

    chatApi.listMyChats.mockResolvedValue({
      chats: [
        { id: 'chat-a', name: 'Chat A' },
        { id: 'chat-b', name: 'Chat B' },
      ],
    });
    chatApi.listChatSessions.mockImplementation((chatId) => {
      if (chatId === 'chat-a') return firstChatSessions.promise;
      if (chatId === 'chat-b') return secondChatSessions.promise;
      return Promise.resolve({ sessions: [] });
    });

    render(<HookHarness />);

    await waitFor(() => expect(screen.getByTestId('selected-chat')).toHaveTextContent('chat-a'));
    await waitFor(() => expect(chatApi.listChatSessions).toHaveBeenCalledWith('chat-a'));

    await user.click(screen.getByTestId('select-chat-b'));

    await waitFor(() => expect(screen.getByTestId('selected-chat')).toHaveTextContent('chat-b'));
    await waitFor(() => expect(chatApi.listChatSessions).toHaveBeenCalledWith('chat-b'));

    await act(async () => {
      secondChatSessions.resolve({
        sessions: [{ id: 'session-b', name: 'Session B', messages: [] }],
      });
      await secondChatSessions.promise;
    });

    await waitFor(() => expect(screen.getByTestId('selected-session')).toHaveTextContent('session-b'));
    expect(screen.getByTestId('session-count')).toHaveTextContent('1');

    await act(async () => {
      firstChatSessions.resolve({ sessions: [] });
      await firstChatSessions.promise;
    });

    await waitFor(() => expect(screen.getByTestId('selected-chat')).toHaveTextContent('chat-b'));
    expect(screen.getByTestId('selected-session')).toHaveTextContent('session-b');
    expect(screen.getByTestId('session-count')).toHaveTextContent('1');
  });
});
