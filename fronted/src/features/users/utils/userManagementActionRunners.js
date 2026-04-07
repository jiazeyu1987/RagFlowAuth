export const runWithClearedKbDirectoryError = (
  clearKbDirectoryCreateError,
  action,
  ...args
) => {
  clearKbDirectoryCreateError?.();
  return action(...args);
};

export const runStateAction = (
  setState,
  buildNextState,
  ...args
) => setState(buildNextState(...args));

export const bindStateAction = (
  setState,
  buildNextState
) => (
  ...args
) => runStateAction(
  setState,
  buildNextState,
  ...args
);

export const bindKbDirectoryErrorClearedAction = (
  clearKbDirectoryCreateError,
  action
) => (
  ...args
) => runWithClearedKbDirectoryError(
  clearKbDirectoryCreateError,
  action,
  ...args
);

export const bindKbDirectoryErrorClearedActions = (
  clearKbDirectoryCreateError,
  actions
) => Object.fromEntries(
  Object.entries(actions).map(([key, action]) => [
    key,
    bindKbDirectoryErrorClearedAction(clearKbDirectoryCreateError, action),
  ])
);

export const bindKbDirectoryErrorClearedStateAction = (
  clearKbDirectoryCreateError,
  setState,
  buildNextState
) => (
  ...args
) => runWithClearedKbDirectoryError(
  clearKbDirectoryCreateError,
  () => runStateAction(setState, buildNextState, ...args)
);

export const bindFormErrorsClearedDraftAction = (
  setError,
  clearKbDirectoryCreateError,
  setState,
  applyChange
) => (
  ...args
) => runWithClearedFormErrors(
  setError,
  clearKbDirectoryCreateError,
  setState,
  (previousState) => applyChange(previousState, ...args)
);


export const runWithClearedFormErrors = (
  setError,
  clearKbDirectoryCreateError,
  action,
  ...args
) => {
  setError(null);
  return runWithClearedKbDirectoryError(
    clearKbDirectoryCreateError,
    action,
    ...args
  );
};
