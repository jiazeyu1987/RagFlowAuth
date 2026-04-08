import React from 'react';

import ElectronicSignatureAuthorizationPanel from '../features/electronicSignature/components/ElectronicSignatureAuthorizationPanel';
import ElectronicSignatureFiltersPanel from '../features/electronicSignature/components/ElectronicSignatureFiltersPanel';
import ElectronicSignatureHeader from '../features/electronicSignature/components/ElectronicSignatureHeader';
import ElectronicSignatureSignaturesWorkspace from '../features/electronicSignature/components/ElectronicSignatureSignaturesWorkspace';
import { TEXT } from '../features/electronicSignature/electronicSignatureManagementView';
import useElectronicSignatureManagementPage from '../features/electronicSignature/useElectronicSignatureManagementPage';

const ElectronicSignatureManagement = () => {
  const {
    activeTab,
    loading,
    detailLoading,
    verifyLoading,
    error,
    verifyMessage,
    filters,
    displaySignatures,
    total,
    selectedSignatureId,
    selectedSignature,
    authorizationLoading,
    authorizations,
    setActiveTab,
    setFilterValue,
    handleSearch,
    handleReset,
    handleSelectSignature,
    handleVerifySignature,
    handleToggleAuthorization,
  } = useElectronicSignatureManagementPage();

  if (loading) {
    return <div style={{ padding: '12px' }}>{TEXT.loading}</div>;
  }

  return (
    <div style={{ maxWidth: '1400px' }} data-testid="electronic-signature-management-page">
      <ElectronicSignatureHeader
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        error={error}
        verifyMessage={verifyMessage}
      />

      {activeTab === 'signatures' ? (
        <>
          <ElectronicSignatureFiltersPanel
            filters={filters}
            setFilterValue={setFilterValue}
            handleSearch={handleSearch}
            handleReset={handleReset}
            total={total}
          />
          <ElectronicSignatureSignaturesWorkspace
            displaySignatures={displaySignatures}
            selectedSignatureId={selectedSignatureId}
            handleSelectSignature={handleSelectSignature}
            detailLoading={detailLoading}
            selectedSignature={selectedSignature}
            verifyLoading={verifyLoading}
            handleVerifySignature={handleVerifySignature}
          />
        </>
      ) : (
        <ElectronicSignatureAuthorizationPanel
          authorizationLoading={authorizationLoading}
          authorizations={authorizations}
          handleToggleAuthorization={handleToggleAuthorization}
        />
      )}
    </div>
  );
};

export default ElectronicSignatureManagement;
