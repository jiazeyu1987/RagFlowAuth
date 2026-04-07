import {
  bindStateAction,
  bindFormErrorsClearedDraftAction,
  bindKbDirectoryErrorClearedAction,
  bindKbDirectoryErrorClearedActions,
  bindKbDirectoryErrorClearedStateAction,
  runStateAction,
  runWithClearedFormErrors,
  runWithClearedKbDirectoryError,
} from './userManagementActionRunners';

describe('userManagementActionRunners', () => {
  it('clears the kb-directory error before running the action', () => {
    const events = [];
    const clearKbDirectoryCreateError = jest.fn(() => events.push('clear'));
    const action = jest.fn((value) => {
      events.push(`action:${value}`);
      return `done:${value}`;
    });

    const result = runWithClearedKbDirectoryError(
      clearKbDirectoryCreateError,
      action,
      'company-1'
    );

    expect(events).toEqual(['clear', 'action:company-1']);
    expect(result).toBe('done:company-1');
  });

  it('still runs when the clear callback is missing', () => {
    const action = jest.fn(() => 'done');

    expect(runWithClearedKbDirectoryError(undefined, action)).toBe('done');
    expect(action).toHaveBeenCalledTimes(1);
  });

  it('runs state actions by building the next state before applying it', () => {
    const events = [];
    const buildNextState = jest.fn((value) => {
      events.push(`build:${value}`);
      return { value };
    });
    const setState = jest.fn((nextState) => {
      events.push(`state:${nextState.value}`);
      return `done:${nextState.value}`;
    });

    expect(runStateAction(setState, buildNextState, 'company-1')).toBe('done:company-1');
    expect(events).toEqual(['build:company-1', 'state:company-1']);
  });

  it('binds actions that always clear the kb-directory error before execution', () => {
    const events = [];
    const clearKbDirectoryCreateError = jest.fn(() => events.push('clear'));
    const action = jest.fn((value) => {
      events.push(`action:${value}`);
      return `done:${value}`;
    });

    const boundAction = bindKbDirectoryErrorClearedAction(
      clearKbDirectoryCreateError,
      action
    );

    expect(boundAction('company-2')).toBe('done:company-2');
    expect(events).toEqual(['clear', 'action:company-2']);
  });

  it('binds state actions that apply the built state result', () => {
    const events = [];
    const buildNextState = jest.fn((value) => {
      events.push(`build:${value}`);
      return { value };
    });
    const setState = jest.fn((nextState) => {
      events.push(`state:${nextState.value}`);
      return `done:${nextState.value}`;
    });

    const boundAction = bindStateAction(setState, buildNextState);

    expect(boundAction('company-2')).toBe('done:company-2');
    expect(events).toEqual(['build:company-2', 'state:company-2']);
  });

  it('binds action maps that always clear the kb-directory error before execution', () => {
    const events = [];
    const clearKbDirectoryCreateError = jest.fn(() => events.push('clear'));
    const actions = {
      open: jest.fn((value) => {
        events.push(`open:${value}`);
        return `opened:${value}`;
      }),
      close: jest.fn(() => {
        events.push('close');
        return 'closed';
      }),
    };

    const boundActions = bindKbDirectoryErrorClearedActions(
      clearKbDirectoryCreateError,
      actions
    );

    expect(boundActions.open('company-2')).toBe('opened:company-2');
    expect(boundActions.close()).toBe('closed');
    expect(events).toEqual(['clear', 'open:company-2', 'clear', 'close']);
  });

  it('binds state actions that clear kb-directory error before building the next state', () => {
    const events = [];
    const clearKbDirectoryCreateError = jest.fn(() => events.push('clear'));
    const buildNextState = jest.fn((value) => {
      events.push(`build:${value}`);
      return { value };
    });
    const setState = jest.fn((nextState) => {
      events.push(`state:${nextState.value}`);
      return `done:${nextState.value}`;
    });

    const boundAction = bindKbDirectoryErrorClearedStateAction(
      clearKbDirectoryCreateError,
      setState,
      buildNextState
    );

    expect(boundAction('company-3')).toBe('done:company-3');
    expect(events).toEqual(['clear', 'build:company-3', 'state:company-3']);
  });

  it('binds draft changes that clear form and kb-directory errors before applying state updates', () => {
    const events = [];
    const setError = jest.fn((value) => events.push(`error:${value}`));
    const clearKbDirectoryCreateError = jest.fn(() => events.push('clear'));
    const setState = jest.fn((updater) => {
      events.push(`state:${updater({ field: 'before' }).field}`);
    });
    const applyChange = jest.fn((previousState, field) => ({
      ...previousState,
      field,
    }));

    const boundAction = bindFormErrorsClearedDraftAction(
      setError,
      clearKbDirectoryCreateError,
      setState,
      applyChange
    );

    boundAction('after');

    expect(events).toEqual(['error:null', 'clear', 'state:after']);
    expect(applyChange).toHaveBeenCalledWith({ field: 'before' }, 'after');
  });

  it('clears the local form error before clearing kb-directory error and running the action', () => {
    const events = [];
    const setError = jest.fn((value) => events.push(`error:${value}`));
    const clearKbDirectoryCreateError = jest.fn(() => events.push('clear'));
    const action = jest.fn(() => events.push('action'));

    runWithClearedFormErrors(
      setError,
      clearKbDirectoryCreateError,
      action
    );

    expect(events).toEqual(['error:null', 'clear', 'action']);
  });
});
