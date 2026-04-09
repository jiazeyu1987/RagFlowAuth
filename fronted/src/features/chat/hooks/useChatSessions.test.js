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
  const restoreSourcesIntoMessages = React.useCallback((chatId, sessionId, messages) => messages, []);
  const hook = useChatSessions({
    restoreSourcesIntoMessages,
  });

  return (
    <div>
      <div data-testid="selected-chat">{hook.selectedChatId || ''}</div>
      <div data-testid="selected-session">{hook.selectedSessionId || ''}</div>
      <div data-testid="session-count">{hook.sessions.length}</div>
      <button type="button" data-testid="create-session" onClick={() => hook.actions.createSession()}>
        create-session
      </button>
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

    chatApi.listMyChats.mockResolvedValue([
      { id: 'chat-a', name: 'Chat A' },
      { id: 'chat-b', name: 'Chat B' },
    ]);
    chatApi.listChatSessions.mockImplementation((chatId) => {
      if (chatId === 'chat-a') return firstChatSessions.promise;
      if (chatId === 'chat-b') return secondChatSessions.promise;
      return Promise.resolve([]);
    });

    render(<HookHarness />);

    await waitFor(() => expect(screen.getByTestId('selected-chat')).toHaveTextContent('chat-a'));
    await waitFor(() => expect(chatApi.listChatSessions).toHaveBeenCalledWith('chat-a'));

    await user.click(screen.getByTestId('select-chat-b'));

    await waitFor(() => expect(screen.getByTestId('selected-chat')).toHaveTextContent('chat-b'));
    await waitFor(() => expect(chatApi.listChatSessions).toHaveBeenCalledWith('chat-b'));

    await act(async () => {
      secondChatSessions.resolve([{ id: 'session-b', name: 'Session B', messages: [] }]);
      await secondChatSessions.promise;
    });

    await waitFor(() => expect(screen.getByTestId('selected-session')).toHaveTextContent('session-b'));
    expect(screen.getByTestId('session-count')).toHaveTextContent('1');

    await act(async () => {
      firstChatSessions.resolve([]);
      await firstChatSessions.promise;
    });

    await waitFor(() => expect(screen.getByTestId('selected-chat')).toHaveTextContent('chat-b'));
    expect(screen.getByTestId('selected-session')).toHaveTextContent('session-b');
    expect(screen.getByTestId('session-count')).toHaveTextContent('1');
  });

  it('keeps newly created session when stale fetch resolves later', async () => {
    const user = userEvent.setup();
    const initialSessions = deferred();

    chatApi.listMyChats.mockResolvedValue([
      { id: 'chat-a', name: 'Chat A' },
    ]);
    chatApi.listChatSessions.mockImplementation((chatId) => {
      if (chatId === 'chat-a') return initialSessions.promise;
      return Promise.resolve([]);
    });
    chatApi.createChatSession.mockResolvedValue({ id: 'session-new', name: 'New Session', messages: [] });

    render(<HookHarness />);

    await waitFor(() => expect(screen.getByTestId('selected-chat')).toHaveTextContent('chat-a'));
    await waitFor(() => expect(chatApi.listChatSessions).toHaveBeenCalledWith('chat-a'));

    await user.click(screen.getByTestId('create-session'));

    await waitFor(() => expect(chatApi.createChatSession).toHaveBeenCalledWith('chat-a', '\u65b0\u5bf9\u8bdd'));
    await waitFor(() => expect(screen.getByTestId('selected-session')).toHaveTextContent('session-new'));
    expect(screen.getByTestId('session-count')).toHaveTextContent('1');

    await act(async () => {
      initialSessions.resolve([]);
      await initialSessions.promise;
    });

    expect(screen.getByTestId('selected-session')).toHaveTextContent('session-new');
    expect(screen.getByTestId('session-count')).toHaveTextContent('1');
  });

  it('does not overwrite a user-selected chat when chat list resolves later', async () => {
    const user = userEvent.setup();
    const chatsDeferred = deferred();

    chatApi.listMyChats.mockImplementation(() => chatsDeferred.promise);
    chatApi.listChatSessions.mockResolvedValue([]);

    render(<HookHarness />);

    await user.click(screen.getByTestId('select-chat-b'));
    expect(screen.getByTestId('selected-chat')).toHaveTextContent('chat-b');

    await act(async () => {
      chatsDeferred.resolve([
        { id: 'chat-a', name: 'Chat A' },
        { id: 'chat-b', name: 'Chat B' },
      ]);
      await chatsDeferred.promise;
    });

    await waitFor(() => expect(screen.getByTestId('selected-chat')).toHaveTextContent('chat-b'));
  });
});
