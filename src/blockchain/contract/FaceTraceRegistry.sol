// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

contract FaceTraceRegistry {
    struct Record {
        string fingerprint;
        string matchedPostUrl;
        uint256 timestamp;
        address submitter;
    }

    // recordId (auto-incrementing) => Record
    mapping(uint256 => Record) public records;
    uint256 public recordCount;

    event RecordStored(uint256 indexed recordId, string fingerprint, address indexed submitter);

    function storeRecord(string memory _fingerprint, string memory _matchedPostUrl) public returns (uint256) {
        uint256 newId = recordCount;
        records[newId] = Record({
            fingerprint: _fingerprint,
            matchedPostUrl: _matchedPostUrl,
            timestamp: block.timestamp,
            submitter: msg.sender
        });
        recordCount += 1;

        emit RecordStored(newId, _fingerprint, msg.sender);
        return newId;
    }

    function getRecord(uint256 _recordId) public view returns (
        string memory fingerprint,
        string memory matchedPostUrl,
        uint256 timestamp,
        address submitter
    ) {
        Record memory r = records[_recordId];
        return (r.fingerprint, r.matchedPostUrl, r.timestamp, r.submitter);
    }
}