# GeneLedger-DAO 🧬🔗

A decentralized autonomous organization (DAO) designed for genomic research. GeneLedger-DAO expands on the GeneLedger concept by providing a secure, transparent platform where researchers can query genomic data and data owners are automatically compensated via smart contracts, empowering a new model for collaborative and ethical scientific discovery.

-----

## ✨ Features

  * **Decentralized Data Marketplace:** Enables a peer-to-peer ecosystem for genomic data, eliminating the need for a central authority.
  * **Automated Compensation:** Data owners are automatically and transparently compensated via on-chain smart contracts for every query of their data.
  * **Privacy-Preserving Access:** An **Access Control Agent** enforces strict privacy rules, while genomic data is stored in **off-chain encrypted shards**.
  * **Intelligent Querying:** A **Query Agent** translates complex research questions into efficient vector searches using hybrid search with **Weaviate**, combining both semantic and keyword capabilities.
  * **On-Chain Governance:** The system's rules and decision-making are managed by a DAO, allowing the community to govern the platform's evolution.

-----

## ⚙️ Tech Stack

  * **Frontend & Framework:** Next.js (MERN Stack)
  * **Styling:** Tailwind CSS
  * **Language:** TypeScript
  * **Blockchain/Smart Contracts:** Solana + Anchor
  * **Vector Database:** Weaviate
  * **Local Data Caching:** LanceDB
  * **Core Logic:** Rust

-----

## 🚀 Getting Started

### Prerequisites

  * Rust
  * Node.js (for Solana CLI)
  * Docker (for Weaviate)
  * Solana CLI

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/saadsalmanakram/GeneLedger-DAO.git
    cd GeneLedger-DAO
    ```
2.  **Start Docker containers:**
    ```bash
    docker-compose up -d
    ```
3.  **Build the smart contract:**
    ```bash
    cd programs/geneledger-dao
    anchor build
    ```
4.  **Set up the agents:**
    Follow the instructions in the `agents/` directory to build the core Rust-based agents.

### Configuration

Set up your Solana wallet and configure the smart contract address in the `Anchor.toml` file.

### Usage

Interact with the DAO by using the CLI tools provided in the `cli/` directory to register data, submit queries, and receive payments.

-----

