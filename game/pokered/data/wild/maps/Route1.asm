Route1WildMons:
; "Starter Forest" -- right north of Pallet Town: all three starters plus fan
; favourites, at low levels so they're catchable immediately. (Custom for the
; educational build.)
	def_grass_wildmons 25 ; encounter rate
	db  5, PIKACHU
	db  5, EEVEE
	db  5, BULBASAUR
	db  5, CHARMANDER
	db  5, SQUIRTLE
	db  6, GROWLITHE
	db  6, VULPIX
	db  6, DRATINI
	db  4, PIDGEY
	db  3, RATTATA
	end_grass_wildmons

	def_water_wildmons 0 ; encounter rate
	end_water_wildmons
