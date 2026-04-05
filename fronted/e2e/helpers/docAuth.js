// @ts-check
const {
  companyAdminStorageStatePath,
  companyAdminTest,
  operatorStorageStatePath,
  operatorTest,
  reviewerStorageStatePath,
  reviewerTest,
  subAdminStorageStatePath,
  subAdminTest,
  uploaderStorageStatePath,
  uploaderTest,
  untrainedReviewerStorageStatePath,
  untrainedReviewerTest,
  viewerStorageStatePath,
  viewerTest,
} = require('./auth');

module.exports = {
  companyAdminStorageStatePath,
  operatorStorageStatePath,
  reviewerStorageStatePath,
  subAdminStorageStatePath,
  uploaderStorageStatePath,
  untrainedReviewerStorageStatePath,
  viewerStorageStatePath,
  docAdminTest: companyAdminTest,
  docOperatorTest: operatorTest,
  docReviewerTest: reviewerTest,
  docSubAdminTest: subAdminTest,
  docUploaderTest: uploaderTest,
  docUntrainedReviewerTest: untrainedReviewerTest,
  docViewerTest: viewerTest,
};
