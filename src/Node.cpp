//===- Node.cpp -------------------------------------------------*- C++ -*-===//
//
//  Copyright (C) 2020 GrammaTech, Inc.
//
//  This code is licensed under the MIT license. See the LICENSE file in the
//  project root for license terms.
//
//  This project is sponsored by the Office of Naval Research, One Liberty
//  Center, 875 N. Randolph Street, Arlington, VA 22203 under contract #
//  N68335-17-C-0700.  The content of the information does not necessarily
//  reflect the position or policy of the Government and no official
//  endorsement should be inferred.
//
//===----------------------------------------------------------------------===//
#include "Node.hpp"
#include "gtirb/CodeBlock.hpp"
#include "gtirb/DataBlock.hpp"
#include "gtirb/IR.hpp"
#include "gtirb/Module.hpp"
#include "gtirb/Section.hpp"
#include "gtirb/SymbolicExpression.hpp"
#include <boost/uuid/uuid_generators.hpp>

using namespace gtirb;

// TODO: accessing this object between threads requires synchronization.
static boost::uuids::random_generator UUIDGenerator;

Node::Node(Context& C, Kind Knd) : K(Knd), Uuid(UUIDGenerator()), Ctx(&C) {
  Ctx->registerNode(Uuid, this);
}

Node::~Node() noexcept { Ctx->unregisterNode(this); }

void Node::setUUID(UUID X) {
  // UUID should not previously exist
  assert(Ctx->findNode(X) == nullptr && "UUID already registered");

  Ctx->unregisterNode(this);
  this->Uuid = X;
  Ctx->registerNode(Uuid, this);
}

template <typename NodeType, typename CollectionType>
static void modifyIndex(CollectionType& Index, NodeType* N,
                        const std::function<void()>& F) {
  if (auto It = Index.find(N); It != Index.end()) {
    Index.modify(It, [&F](const auto&) { F(); });
  } else {
    F();
  }
}

// FIXME: It would also be nice to be more discerning about what indices to
// update, so we invalidate only the minimum of iterators. Right now, modifying
// many properties invalidates more iterators that it strictly needs to.

void Node::addToIndices() {
  switch (getKind()) {
  case Node::Kind::CodeBlock: {
    auto* B = cast<CodeBlock>(this);

    auto* BI = B->getByteInterval();
    if (!BI) {
      return;
    }

    auto* S = BI->getSection();
    if (!S) {
      return;
    }

    auto* M = S->getModule();
    if (!M) {
      return;
    }

    // Update symbol referents.
    // Note that we update the symbol's address index while iterating over its
    // referent index, so one doesn't invalidate the other.
    for (auto& Sym : M->findSymbols(*B)) {
      modifyIndex(M->Symbols.get<Module::by_pointer>(), &Sym, []() {});
    }

  } break;
  case Node::Kind::DataBlock: {
    auto* B = cast<DataBlock>(this);

    auto* BI = B->getByteInterval();
    if (!BI) {
      return;
    }

    auto* S = BI->getSection();
    if (!S) {
      return;
    }

    auto* M = S->getModule();
    if (!M) {
      return;
    }

    // Update symbol referents.
    // Note that we update the symbol's address index while iterating over its
    // referent index, so one doesn't invalidate the other.
    for (auto& Sym : M->findSymbols(*B)) {
      modifyIndex(M->Symbols.get<Module::by_pointer>(), &Sym, []() {});
    }
  } break;
  default: { assert(!"unexpected kind of node passed to addToModuleIndices!"); }
  }
}

void Node::mutateIndices(const std::function<void()>& F) {
  switch (getKind()) {
  case Node::Kind::ByteInterval: {
    F();

    auto* BI = cast<ByteInterval>(this);
    auto* S = BI->getSection();
    if (!S) {
      return;
    }

    // Symbols may need their address index updated if they refer to a block
    // inside this BI.
    // Note that we update the symbol's address index while iterating over its
    // referent index, so one doesn't invalidate the other.
    auto* M = S->getModule();
    if (!M) {
      return;
    }

    for (auto& B : BI->blocks()) {
      for (auto& Sym : M->findSymbols(B)) {
        modifyIndex(M->Symbols.get<Module::by_pointer>(), &Sym, []() {});
      }
    }
  } break;
  case Node::Kind::Symbol: {
    auto* S = cast<Symbol>(this);
    auto* M = S->getModule();
    if (!M) {
      F();
      return;
    }
    modifyIndex(M->Symbols.get<Module::by_pointer>(), S, F);
  } break;
  default: {
    assert(!"unexpected kind of node passed to mutateModuleIndices!");
  }
  }
}

void Node::removeFromIndices() {
  switch (getKind()) {
  case Node::Kind::CodeBlock: {
    auto* B = cast<CodeBlock>(this);

    auto* BI = B->getByteInterval();
    if (!BI) {
      return;
    }

    auto* S = BI->getSection();
    if (!S) {
      return;
    }

    auto* M = S->getModule();
    if (!M) {
      return;
    }

    // Update symbol referents.
    // Note that we update the symbol's address index while iterating over its
    // referent index, so one doesn't invalidate the other.
    for (auto& Sym : M->findSymbols(*B)) {
      modifyIndex(M->Symbols.get<Module::by_pointer>(), &Sym, []() {});
    }

    // Update CFG.
    if (IR* P = M->getIR()) {
      removeVertex(B, P->Cfg);
    }
  } break;
  case Node::Kind::DataBlock: {
    auto* B = cast<DataBlock>(this);

    auto* BI = B->getByteInterval();
    if (!BI) {
      return;
    }

    auto* S = BI->getSection();
    if (!S) {
      return;
    }

    auto* M = S->getModule();
    if (!M) {
      return;
    }

    // Update symbol referents.
    // Note that we update the symbol's address index while iterating over its
    // referent index, so one doesn't invalidate the other.
    for (auto& Sym : M->findSymbols(*B)) {
      modifyIndex(M->Symbols.get<Module::by_pointer>(), &Sym, []() {});
    }
  } break;
  default: {
    assert(!"unexpected kind of node passed to mutateModuleIndices!");
  }
  }
}
