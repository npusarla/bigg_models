from theseus import models
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
from sqlalchemy import create_engine

from model import Model, Component, Reaction, Compartment, Metabolite, Compartmentalized_Component, Model_Reaction, Reaction_Matrix, Gene, Model_Compartmentalized_Component, Model_Gene, GPR_Matrix
Session = sessionmaker()

engine = create_engine("postgresql://dbuser@localhost:5432/bigg2")

Session.configure(bind=engine)

class IndependentObjects:

	def loadGenes(self, modellist, session):
		for model in modellist:
			for gene in model.genes:
				geneObject = Gene(name = gene.id)
				session.add(geneObject)
	
	def loadModels(self, modellist, session):
		for model in modellist:
			modelObject = Model(name = model.id, firstcreated = '2008-11-11 13:23:44')
			session.add(modelObject)
			
	def loadComponents(self, modellist, session):
		for m in modellist:
			for component in m.metabolites:
				if not session.query(Component).filter(Component.identifier == component.id).count():
					componentObject = Component(identifier = component.id, name = component.name, formula = str(component.formula))
					session.add(componentObject)
				
	def loadReactions(self , modellist, session):
		for model in modellist:
			for reaction in model.reactions:
				reactionObject = Reaction(name = reaction.id, long_name = reaction.name)
				session.add(reactionObject)
	
	def loadCompartments(self, modellist, session):
		for model in modellist:
			for component in model.metabolites:
				if not session.query(Compartment).filter(Compartment.name == component.id[-1:len(component.id)]).count():
					compartmentObject = Compartment(name = component.id[-1:len(component.id)])
					session.add(compartmentObject)
					

class DependentObjects:
	def loadMetabolites(self, modellist, session):
		for instance in session.query(Component):
			metaboliteObject = Metabolite(id = instance.id)
			session.add(metaboliteObject)

	def loadModelGenes(self, modellist, session):
		for model in modellist:
			for gene in model.genes:
				genequery = session.query(Gene).filter(Gene.name == gene.id).first()
				modelquery = session.query(Model).filter(Model.name == model.id).first()
				object = Model_Gene(model_id = modelquery.id, gene_id = genequery.id)
				session.add(object)
				

	
	def loadCompartmentalizedComponent(self, modellist, session):		
		for component in session.query(Component):
			identifier = session.query(Compartment).filter(Compartment.name == component.identifier[-1:len(component.identifier)]).first()
			#instance = session.query(Component).filter(Component.identifier == component.identifier[:-2]).first()
			object = Compartmentalized_Component(component_id = component.id, compartment_id = identifier.id)
			session.add(object)
				
	def loadModelCompartmentalizedComponent(self, modellist, session):
		for model in modellist:
			for metabolite in model.metabolites:
				componentquery = session.query(Component).filter(Component.identifier == metabolite.id).first()
				compartmentalized_component_query = session.query(Compartmentalized_Component).filter(Compartmentalized_Component.component_id == componentquery.id).first()
				modelquery = session.query(Model).filter(Model.name == model.id).first()
				object = Model_Compartmentalized_Component(model_id = modelquery.id, compartmentalized_component_id = compartmentalized_component_query.id)
				session.add(object)


	def loadModelReaction(self, modellist, session):
		for model in modellist:
			for reaction in model.reactions:
				reactionquery = session.query(Reaction).filter(Reaction.name == reaction.id).first()
				modelquery = session.query(Model).filter(Model.name == model.id).first()
				object = Model_Reaction(reaction_id = reactionquery.id, model_id = modelquery.id, name = reaction.id, upperbound = reaction.upper_bound, lowerbound = reaction.lower_bound, gpr = reaction.gene_reaction_rule)
				session.add(object)
			
	
	def loadGPRMatrix(self, modellist, session):
	    for model in modellist:
	        for reaction in model.reactions:
	            for gene in reaction._genes.keys():
	                model_gene_query = session.query(Model_Gene).join(Gene).filter(Gene.name == gene.name).first()
	                model_reaction_query = session.query(Model_Reaction).filter(Model_Reaction.name == reaction.id).first()
	                object = GPR_Matrix(model_gene_id = model_gene_query.gene_id, model_reaction_id = model_reaction_query.id) 
	                session.add(object)
						
	def loadReactionMatrix(self, modellist, session):
		for model in modellist:
			for metabolite in model.metabolites:
				for reaction in metabolite._reaction:
					componentquery = session.query(Component).filter(Component.identifier == metabolite.id).first()
					compartmentalized_component_query = session.query(Compartmentalized_Component).filter(Compartmentalized_Component.component_id == componentquery.id).first()
					#modelquery = session.query(Model).filter(Model.name == model.id).first()
					reactionquery = session.query(Reaction).filter(Reaction.name == reaction.id).first()
					
					for stoichKey in reaction._metabolites.keys():
						if stoichKey == metabolite.id:
							stoichiometryobject = reaction._metabolites[stoichKey]
					object = Reaction_Matrix(reaction_id = reactionquery.id, compartmentalized_component_id = compartmentalized_component_query.id, stoichiometry = stoichiometryobject)
					session.add(object)
					
		"""
		insert a model and all its reactions and compartmentalized component id
		x = select component.id where component.name = reaction.component
		y = select compartment.id where compartment.name = reaction.compartment
		z = select compartmentalized component where component = x and compartment = y
		insert ReactionMatrix(model.id, model.reaction, z)
		"""
		
@contextmanager
def create_Session():
	session = Session()
	try:
		yield session
		session.commit()
	except:
		session.rollback()
		raise
	finally:
		session.close()
		
def run_program():
	modelObjectList = []
	for m in models.get_model_list():
		modelObjectList.append(models.load_model(m))
	with create_Session() as session:
		IndependentObjects().loadModels(modelObjectList, session)
		IndependentObjects().loadGenes(modelObjectList, session)
		IndependentObjects().loadComponents(modelObjectList,session)
		IndependentObjects().loadCompartments(modelObjectList, session)
		IndependentObjects().loadReactions(modelObjectList, session)
		DependentObjects().loadMetabolites(modelObjectList, session)
		DependentObjects().loadModelGenes(modelObjectList, session)		
		DependentObjects().loadCompartmentalizedComponent(modelObjectList, session)
		DependentObjects().loadModelReaction(modelObjectList, session)
		DependentObjects().loadReactionMatrix(modelObjectList, session)
		DependentObjects().loadGPRMatrix(modelObjectList, session)
		DependentObjects().loadModelCompartmentalizedComponent(modelObjectList, session)
		
if __name__ == '__main__':
	run_program()